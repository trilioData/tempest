import os
import sys
import time

from oslo_log import log as logging

from tempest import config
from tempest import reporting
from tempest import tvaultconf
from tempest.api.workloadmgr import base
from tempest.lib import decorators

sys.path.append(os.getcwd())

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    def _create_workload(self):
        try:
            self.wid = self.workload_create([self.vm_id],
                    tvaultconf.workload_type_id)
            LOG.debug(f"Workload ID: {self.wid}")
        except Exception as e:
            LOG.error(f"Exception: {e}")
            raise Exception("Create workload")
        if(self.wid is not None):
            self.wait_for_workload_tobe_available(self.wid)
            self.workload_status = self.getWorkloadStatus(self.wid)
            if(self.workload_status == "available"):
                reporting.add_test_step("Create workload", tvaultconf.PASS)
            else:
                raise Exception("Create workload")
        else:
            raise Exception("Create workload")

    def _create_snapshot(self, snapshot_type):
        if snapshot_type.lower() == 'full':
            is_full = True
        else:
            is_full = False
        self.snapshot_id = self.workload_snapshot(self.wid, is_full)
        self.wait_for_workload_tobe_available(self.wid)
        self.snapshot_status = self.getSnapshotStatus(self.wid,
                self.snapshot_id)
        if(self.snapshot_status == "available"):
            reporting.add_test_step(f"Create {snapshot_type} snapshot",
                    tvaultconf.PASS)
        else:
            raise Exception(f"Create {snapshot_type} snapshot")
        return self.snapshot_id

    def _verify_post_restore(self, images_list_bf, images_list_af,
            key_pair_list_bf, key_pair_list_af, md5sums_bf, md5sums_af,
            test_id):
        tmp_fail = False
        if images_list_bf == images_list_af:
            reporting.add_test_step(
                "Image properties intact after restore", tvaultconf.PASS)
        else:
            reporting.add_test_step(
                "Image properties not restored properly", tvaultconf.FAIL)
            tmp_fail = True

        if key_pair_list_bf == key_pair_list_af:
            reporting.add_test_step(
                "Keypair restored properly", tvaultconf.PASS)
        else:
            reporting.add_test_step(
                "Keypair not restored properly", tvaultconf.FAIL)
            tmp_fail = True

        #md5sum verification
        if md5sums_bf == md5sums_af:
            reporting.add_test_step("Md5sum verification", tvaultconf.PASS)
        else:
            reporting.add_test_step("Md5sum verification", tvaultconf.FAIL)
            tmp_fail = True
        
        if tmp_fail:
            reporting.set_test_script_status(tvaultconf.FAIL)
        else:
            if test_id != "":
                self.tests[test_id][1] = 1
        reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_1_glanceimage_restore(self):
        try:
            reporting.add_test_script(str(__name__)+"_vm_reboot")
            self.image_name = "tempest_test_image"
            self.image_id = self.create_image(image_name=self.image_name,
                                    image_cleanup=False)
            LOG.debug(f"Image ID: {self.image_id}")
            if not self.image_id:
                raise Exception("Image not created")
            self.ssh_username = "ubuntu"
            self.kp = self.create_key_pair()
            self.flavor_id = self.create_flavor(tvaultconf.flavor_name,
                                    20, 2, 2048, 0, 1)
            self.original_flavor_conf = self.get_flavor_details(self.flavor_id)
            self.vm_id = self.create_vm(image_id=self.image_id,
                                flavor_id=self.flavor_id,
                                key_pair=self.kp)
            LOG.debug(f"VM ID: {self.vm_id}")
            self.volumes = []
            fip = self.get_floating_ips()
            LOG.debug("\nAvailable floating ips are {}: \n".format(fip))
            if len(fip) < 3:
                raise Exception("Floating ips unavailable")
            self.set_floating_ip(fip[0], self.vm_id)

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0],
                        self.ssh_username)
            self.install_qemu(ssh)
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 2)
            md5sums_before_full = self.calculatemmd5checksum(ssh, "/opt")
            LOG.debug(f"md5sums_before_full: {md5sums_before_full}")
            ssh.close()

            self.reboot_instance(self.vm_id)
            time.sleep(45)
            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0],
                        self.ssh_username)
            md5sums_after_reboot = self.calculatemmd5checksum(ssh, "/opt")
            LOG.debug(f"md5sums_after_reboot: {md5sums_after_reboot}")
            ssh.close()

            if md5sums_before_full == md5sums_after_reboot:
                reporting.add_test_step(
                        "File present after reboot", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                        "File not present after reboot", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # Create workload with API
            self._create_workload()

            #Create full snapshot
            self.snapshot_id = self._create_snapshot(snapshot_type='full')

            images_list_bf = self.list_images()
            LOG.debug(f"images_list_bf: {images_list_bf}")
            self.delete_image(self.image_id)

            #selective restore
            rest_details = {}
            rest_details['rest_type'] = 'selective'
            rest_details['network_id'] = CONF.network.internal_network_id
            rest_details['subnet_id'] = self.get_subnet_id(
                CONF.network.internal_network_id)
            rest_details['instances'] = {self.vm_id: self.volumes}

            payload = self.create_restore_json(rest_details)
            # Trigger selective restore of full snapshot
            restore_id_1 = self.snapshot_selective_restore(
                self.wid, self.snapshot_id,
                restore_name="selective_restore_full_snap",
                instance_details=payload['instance_details'],
                network_details=payload['network_details'])
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id)
            if(self.getRestoreStatus(self.wid, self.snapshot_id,
                    restore_id_1) == "available"):
                reporting.add_test_step("Selective restore of full snapshot",
                        tvaultconf.PASS)
                vm_list = self.get_restored_vm_list(restore_id_1)
                LOG.debug("Restored vm(selective) ID : " + str(vm_list))
                time.sleep(60)
                self.set_floating_ip(fip[1], vm_list[0])
                LOG.debug("Floating ip assigned to selective restored vm -> " +\
                        f"{fip[1]}")
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[1],
                            self.ssh_username)
                md5sums_after_full_selective = self.calculatemmd5checksum(ssh, "/opt")
                LOG.debug(f"md5sums_after_full_selective: {md5sums_after_full_selective}")
                ssh.close()

                if md5sums_before_full == \
                        md5sums_after_full_selective:
                    reporting.add_test_step(
                        "File present on restored instance", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "File not present on restored instance", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                raise Exception("Selective restore of full snapshot")
            reporting.test_case_to_write()

            reporting.add_test_script(str(__name__)+"_delete_image")
            images_list_af = self.list_images()
            LOG.debug(f"images_list_af: {images_list_af}")
            restored_image_id = images_list_af[0]['id']

            attributes = ['visibility', 'name', 'size', 'virtual_size',
                        'checksum', 'os_hash_value', 'id', 'created_at',
                        'updated_at', 'self', 'file', 'direct_url']
            for attr in attributes:
                if attr in images_list_bf[0]:
                    del images_list_bf[0][attr]
                if attr in images_list_af[0]:
                    del images_list_af[0][attr]

            if images_list_bf == images_list_af:
                reporting.add_test_step(
                    "Image properties intact after restore", tvaultconf.PASS)
            else:
                LOG.error(f"images_list_bf: {images_list_bf} and " +\
                        f"images_list_af: {images_list_af}")
                reporting.add_test_step(
                    "Image properties not restored properly", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_2_glanceimage_volume_booted_instance(self):
        try:
            test_var = "tempest.api.workloadmgr.barbican.test_volume_booted_"
            self.tests = [[test_var+"selective_restore_api", 0],
                    [test_var+"oneclickrestore_api", 0]]
            reporting.add_test_script(self.tests[0][0])
            self.image_name = "tempest_test_image"
            self.image_id = self.create_image(image_name=self.image_name,
                                    image_cleanup=False)
            LOG.debug(f"Image ID: {self.image_id}")
            if not self.image_id:
                raise Exception("Image not created")
            self.ssh_username = "ubuntu"
            self.kp = self.create_key_pair(keypair_cleanup=False)
            self.old_flavor_id = self.get_flavor_id(tvaultconf.flavor_name)
            self.delete_flavor(self.old_flavor_id)
            self.flavor_id = self.create_flavor(tvaultconf.flavor_name,
                                    20, 2, 2048, 1536, 1, flavor_cleanup=False)
            self.original_flavor_conf = self.get_flavor_details(self.flavor_id)
            LOG.debug(f"original_flavor_conf: {self.original_flavor_conf}")
            self.boot_volume_id = self.create_volume(
                size=tvaultconf.bootfromvol_vol_size,
                image_id=self.image_id,
                volume_cleanup=False)
            self.set_volume_as_bootable(self.boot_volume_id)
            LOG.debug("Bootable Volume ID : " + str(self.boot_volume_id))

            self.block_mapping_details = [{"source_type": "volume",
                                           "delete_on_termination": "false",
                                           "boot_index": 0,
                                           "uuid": self.boot_volume_id,
                                           "destination_type": "volume"}]

            self.vm_id = self.create_vm(
                key_pair=self.kp,
                image_id="",
                flavor_id=self.flavor_id,
                block_mapping_data=self.block_mapping_details,
                vm_cleanup=False)
            LOG.debug(f"VM ID : {self.vm_id}")

            fip = self.get_floating_ips()
            LOG.debug("\nAvailable floating ips are {}: \n".format(fip))
            if len(fip) < 3:
                raise Exception("Floating ips unavailable")
            self.set_floating_ip(fip[0], self.vm_id)

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0],
                        self.ssh_username)
            self.install_qemu(ssh)
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 2)
            md5sums_before_full = self.calculatemmd5checksum(ssh, "/opt")
            LOG.debug(f"md5sums_before_full: {md5sums_before_full}")
            ssh.close()

            # Create workload with API
            self._create_workload()

            #Create full snapshot
            self.snapshot_id = self._create_snapshot(snapshot_type='full')

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0],
                        self.ssh_username)
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 3)
            md5sums_before_incr = self.calculatemmd5checksum(ssh, "/opt")
            LOG.debug(f"md5sums_before_incr: {md5sums_before_incr}")
            ssh.close()

            #Create incremental snapshot
            self.snapshot_id2 = self._create_snapshot(snapshot_type='incremental')

            #Fetch list of images, keypairs and flavor before restore
            restored_image_id = None
            images_list_bf = self.list_images()
            LOG.debug(f"images_list_bf: {images_list_bf}")
            key_pair_list_bf = self.list_key_pairs()
            LOG.debug(f"key_pair_list_bf: {key_pair_list_bf}")

            #Delete original image, keypair and flavor
            self.delete_image(self.image_id)
            self.delete_flavor(self.flavor_id)
            self.delete_key_pair(tvaultconf.key_pair_name)
            LOG.debug("Delete original image, flavor & keypair")

            #selective restore of full snapshot
            rest_details = {}
            rest_details['rest_type'] = 'selective'
            rest_details['network_id'] = CONF.network.internal_network_id
            rest_details['subnet_id'] = self.get_subnet_id(
                CONF.network.internal_network_id)
            self.volumes = [self.boot_volume_id]
            rest_details['instances'] = {self.vm_id: self.volumes}
            rest_details['flavor'] = self.original_flavor_conf

            payload = self.create_restore_json(rest_details)
            # Trigger selective restore of full snapshot
            restore_id_1 = self.snapshot_selective_restore(
                self.wid, self.snapshot_id,
                restore_name="selective_restore_full_snap",
                instance_details=payload['instance_details'],
                network_details=payload['network_details'])
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id)
            if(self.getRestoreStatus(self.wid, self.snapshot_id,
                    restore_id_1) == "available"):
                reporting.add_test_step("Selective restore of full snapshot",
                        tvaultconf.PASS)
                vm_list = self.get_restored_vm_list(restore_id_1)
                LOG.debug("Restored vm(selective) ID : " + str(vm_list))
                time.sleep(60)
                self.set_floating_ip(fip[1], vm_list[0])
                LOG.debug("Floating ip assigned to selective restored vm -> " +\
                        f"{fip[1]}")
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[1],
                            self.ssh_username)
                md5sums_after_full_selective = self.calculatemmd5checksum(ssh, "/opt")
                LOG.debug(f"md5sums_after_full_selective: {md5sums_after_full_selective}")
                ssh.close()

                #Verify restored image and keypair details
                images_list_af = self.list_images()
                LOG.debug(f"images_list_af: {images_list_af}")
                restored_image_id = images_list_af[0]['id']
                key_pair_list_af = self.list_key_pairs()
                LOG.debug(f"key_pair_list_af: {key_pair_list_af}")
                flavor_id_af = self.get_flavor_id(tvaultconf.flavor_name)
                LOG.debug(f"flavor_id_af: {flavor_id_af}")

                self._verify_post_restore(self, images_list_bf, images_list_af,
                        key_pair_list_bf, key_pair_list_af, md5sums_before_full,
                        md5sums_after_full_selective, test_id="")
            else:
                reporting.add_test_step("Selective restore of full snapshot",
                        tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            #Delete restored image, keypair and flavor
            if restored_image_id:
                self.delete_image(restored_image_id)
            self.delete_flavor(self.flavor_id)
            self.delete_key_pair(tvaultconf.key_pair_name)
            LOG.debug("Delete restored image, flavor & keypair")

            # Trigger selective restore of incremental snapshot
            restore_id_2 = self.snapshot_selective_restore(
                self.wid, self.snapshot_id2,
                restore_name="selective_restore_incr_snap",
                instance_details=payload['instance_details'],
                network_details=payload['network_details'])
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id2)
            if(self.getRestoreStatus(self.wid, self.snapshot_id2,
                    restore_id_2) == "available"):
                reporting.add_test_step("Selective restore of incremental snapshot",
                        tvaultconf.PASS)
                vm_list = self.get_restored_vm_list(restore_id_2)
                LOG.debug("Restored vm(selective) ID : " + str(vm_list))
                time.sleep(60)
                self.set_floating_ip(fip[2], vm_list[0])
                LOG.debug("Floating ip assigned to selective restored vm -> " +\
                        f"{fip[2]}")
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[2],
                            self.ssh_username)
                md5sums_after_incr_selective = self.calculatemmd5checksum(ssh, "/opt")
                LOG.debug(f"md5sums_after_incr_selective: {md5sums_after_incr_selective}")
                ssh.close()

                #Verify restored image and keypair details
                images_list_af = self.list_images()
                LOG.debug(f"images_list_af: {images_list_af}")
                restored_image_id = images_list_af[0]['id']
                key_pair_list_af = self.list_key_pairs()
                LOG.debug(f"key_pair_list_af: {key_pair_list_af}")
                flavor_id_af = self.get_flavor_id(tvaultconf.flavor_name)
                LOG.debug(f"flavor_id_af: {flavor_id_af}")

                self._verify_post_restore(self, images_list_bf, images_list_af,
                        key_pair_list_bf, key_pair_list_af, md5sums_before_incr,
                        md5sums_after_incr_selective, test_id=0)
            else:
                reporting.add_test_step("Selective restore of incremental snapshot",
                        tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                reporting.test_case_to_write()

            reporting.add_test_script(self.tests[1][0])
            #Delete restored image, keypair and flavor
            if restored_image_id:
                self.delete_image(restored_image_id)
            self.delete_flavor(self.flavor_id)
            self.delete_key_pair(tvaultconf.key_pair_name)
            self.delete_vm(self.vm_id)
            LOG.debug("Delete restored image, flavor, keypair & vm")
            restored_vm_id = []

            #Trigger one click restore of full snapshot
            restore_id_3 = self.snapshot_restore(self.wid, self.snapshot_id)
            if(self.getRestoreStatus(self.wid, self.snapshot_id,
                    restore_id_3) == "available"):
                reporting.add_test_step("Oneclick restore of full snapshot",
                        tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                md5sums_after_full_oneclick = self.calculatemmd5checksum(ssh, "/opt")
                LOG.debug(f"md5sums_after_full_oneclick: {md5sums_after_full_oneclick}")
                ssh.close()

                #Verify restored image and keypair details
                images_list_af = self.list_images()
                LOG.debug(f"images_list_af: {images_list_af}")
                restored_image_id = images_list_af[0]['id']
                key_pair_list_af = self.list_key_pairs()
                LOG.debug(f"key_pair_list_af: {key_pair_list_af}")
                flavor_id_af = self.get_flavor_id(tvaultconf.flavor_name)
                LOG.debug(f"flavor_id_af: {flavor_id_af}")
                restored_vm_id = self.get_restored_vm_list(restore_id_3)
                LOG.debug(f"restored_vm_id: {restored_vm_id}")

                self._verify_post_restore(self, images_list_bf, images_list_af,
                        key_pair_list_bf, key_pair_list_af, md5sums_before_full,
                        md5sums_after_full_oneclick, test_id="")
            else:
                reporting.add_test_step("Oneclick restore of full snapshot",
                        tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            #Delete restored image, keypair and flavor
            if restored_image_id:
                self.delete_image(restored_image_id)
            self.delete_flavor(self.flavor_id)
            self.delete_key_pair(tvaultconf.key_pair_name)
            if len(restored_vm_id):
                self.delete_vm(restored_vm_id[0])
            LOG.debug("Delete restored image, flavor, keypair & vm")

            #Trigger one click restore of incremental snapshot
            restore_id_4 = self.snapshot_restore(self.wid, self.snapshot_id2)
            if(self.getRestoreStatus(self.wid, self.snapshot_id2,
                    restore_id_4) == "available"):
                reporting.add_test_step("Oneclick restore of incremental snapshot",
                        tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                md5sums_after_incr_oneclick = self.calculatemmd5checksum(ssh, "/opt")
                LOG.debug(f"md5sums_after_incr_oneclick: {md5sums_after_incr_oneclick}")
                ssh.close()

                #Verify restored image and keypair details
                images_list_af = self.list_images()
                LOG.debug(f"images_list_af: {images_list_af}")
                restored_image_id = images_list_af[0]['id']
                key_pair_list_af = self.list_key_pairs()
                LOG.debug(f"key_pair_list_af: {key_pair_list_af}")
                flavor_id_af = self.get_flavor_id(tvaultconf.flavor_name)
                LOG.debug(f"flavor_id_af: {flavor_id_af}")
                restored_vm_id = self.get_restored_vm_list(restore_id_4)
                LOG.debug(f"restored_vm_id: {restored_vm_id}")

                self._verify_post_restore(self, images_list_bf, images_list_af,
                        key_pair_list_bf, key_pair_list_af, md5sums_before_incr,
                        md5sums_after_incr_oneclick, test_id=1)
            else:
                reporting.add_test_step("Oneclick restore of incremental snapshot",
                        tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            for test in self.tests:
                if test[1] != 1:
                    reporting.set_test_script_status(tvaultconf.FAIL)
                    reporting.add_test_script(test[0])
                    reporting.test_case_to_write()
