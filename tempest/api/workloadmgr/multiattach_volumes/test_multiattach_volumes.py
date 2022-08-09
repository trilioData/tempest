from datetime import datetime, timedelta
from tempest.api.workloadmgr import base
from tempest import config
from tempest.lib import decorators
import time
from oslo_log import log as logging
from tempest import tvaultconf
from tempest import reporting
from tempest.lib.services.compute import base_compute_client as api_version

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadsTest(base.BaseWorkloadmgrTest):
    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()

    def _set_frm_user(self):
        self.frm_image = list(CONF.compute.fvm_image_ref.keys())[0]
        self.frm_ssh_user = ""
        if "centos" in self.frm_image:
            self.frm_ssh_user = "centos"
        elif "ubuntu" in self.frm_image:
            self.frm_ssh_user = "ubuntu"

    def _add_data_on_instance_and_volume(self, ip_list, full=True):
        md5sums_list = []
        file_count = 5
        if len(ip_list) > 1:
            partition_size = "+3GB"
        else:
            partition_size = ""
        i = 1
        for ip in ip_list:
            ssh = self.SshRemoteMachineConnectionWithRSAKey(ip)

            if full:
                self.install_qemu(ssh)
                self.execute_command_disk_create(ssh, str(ip),
                                                 [tvaultconf.volumes_parts[0]], [tvaultconf.mount_points[0]], i,
                                                 partition_size)
                self.execute_command_disk_mount(ssh, str(ip),
                                                [tvaultconf.volumes_parts[0]], [tvaultconf.mount_points[0]], i)
                file_count = 3

            self.addCustomfilesOnLinuxVM(ssh, "/opt", file_count)
            self.addCustomfilesOnLinuxVM(ssh, tvaultconf.mount_points[0], file_count)
            md5sums = {}
            md5sums['opt'] = self.calculatemmd5checksum(ssh, "/opt")
            md5sums[tvaultconf.mount_points[0]] = self.calculatemmd5checksum(ssh, tvaultconf.mount_points[0])
            ssh.close()
            md5sums_list.append(md5sums)
            i = i + 1

        return md5sums_list

    def _mount_unmount_snapshot(self, ip, full=True):
        if full:
            snapshot_id = self.snapshot_id
            snapshot_type = 'full'
            file = 'File_2'
        else:
            snapshot_id = self.snapshot_id2
            snapshot_type = 'incremental'
            file = 'File_5'

        # Mount snapshot
        mount_status = self.mount_snapshot(
            self.wid, snapshot_id, self.frm_id)
        LOG.debug(f"mount_status for {snapshot_type} snapshot: {mount_status}")
        if mount_status:
            reporting.add_test_step(
                "Snapshot mount of " + snapshot_type + " snapshot", tvaultconf.PASS)
            ssh = self.SshRemoteMachineConnectionWithRSAKey(ip, self.frm_ssh_user)
            output_list = self.validate_snapshot_mount(ssh,
                                                       file_name=file, disk_dir="/opt").decode('UTF-8').split('\n')
            ssh.close()
            flag = {'opt': 0, 'vdb1': 0, 'vdb2': 0}
            for i in output_list:
                if 'vda1.mnt' in i:
                    reporting.add_test_step(
                        "Verify that bootdisk mounted is shown on FVM instance", tvaultconf.PASS)
                    flag['opt'] = 1
                    if file in i:
                        reporting.add_test_step(
                            "Verification of bootdisk file's existance on mounted snapshot", tvaultconf.PASS)
                    else:
                        reporting.add_test_step(
                            "Verification of bootdisk file's existance on mounted snapshot", tvaultconf.FAIL)
                if 'vdb1.mnt' in i:
                    reporting.add_test_step(
                        "Verify that multiattach volume on vm1 mounted is shown on FVM instance", tvaultconf.PASS)
                    flag['vdb1'] = 1
                    if file in i:
                        reporting.add_test_step(
                            "Verification of multiattach volume on vm1 file's existance on mounted snapshot",
                            tvaultconf.PASS)
                    else:
                        reporting.add_test_step(
                            "Verification of multiattach volume on vm1 file's existance on mounted snapshot",
                            tvaultconf.FAIL)
                if 'vdb2.mnt' in i:
                    reporting.add_test_step(
                        "Verify that multiattach volume on vm2 mounted is shown on FVM instance", tvaultconf.PASS)
                    flag['vdb2'] = 1
                    if file in i:
                        reporting.add_test_step(
                            "Verification of multiattach volume on vm2 file's existance on mounted snapshot",
                            tvaultconf.PASS)
                    else:
                        reporting.add_test_step(
                            "Verification of multiattach volume on vm2 file's existance on mounted snapshot",
                            tvaultconf.FAIL)
            for k, v in flag.items():
                if v == 0:
                    reporting.add_test_step("Verify that mountpoint mounted is shown on FVM instance",
                                            tvaultconf.FAIL)
        else:
            reporting.add_test_step(
                "Snapshot mount of " + snapshot_type + " snapshot", tvaultconf.FAIL)

        unmount_status = self.unmount_snapshot(self.wid, snapshot_id)
        LOG.debug("VALUE OF is_unmounted: " + str(unmount_status))
        if unmount_status:
            reporting.add_test_step(
                "Snapshot unmount of " + snapshot_type + " snapshot", tvaultconf.PASS)
            ssh = self.SshRemoteMachineConnectionWithRSAKey(
                ip, self.frm_ssh_user)
            output_list = self.validate_snapshot_mount(ssh)
            ssh.close()

            if output_list == b'':
                reporting.add_test_step(
                    "Unmount " + snapshot_type + " snapshot", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Snapshot unmount of " + snapshot_type + " snapshot", tvaultconf.FAIL)
        else:
            reporting.add_test_step(
                "Snapshot unmount of " + snapshot_type + " snapshot", tvaultconf.FAIL)

    def _check_data_after_restore(self, ip_list, md5sums_list, restore_type):
        md5sums_after_list = []
        i = 1
        for ip in ip_list:
            ssh = self.SshRemoteMachineConnectionWithRSAKey(ip)
            self.execute_command_disk_mount(ssh, ip,
                                            [tvaultconf.volumes_parts[0]], [tvaultconf.mount_points[0]], i)
            md5sums_after_vm = {}
            md5sums_after_vm['opt'] = self.calculatemmd5checksum(ssh, "/opt")
            md5sums_after_vm[tvaultconf.mount_points[0]] = self.calculatemmd5checksum(ssh,
                                                                                      tvaultconf.mount_points[0])
            LOG.debug(
                f"md5sums_after_vm{i}_{restore_type}: {md5sums_after_vm}")
            ssh.close()
            md5sums_after_list.append(md5sums_after_vm)
            i = i + 1

        if restore_type == 'selective':
            tempopt_vm1 = md5sums_after_list[0]['opt']
            tempmp_vm1 = md5sums_after_list[0][tvaultconf.mount_points[0]]
            if len(ip_list) > 1:
                tempopt_vm2 = md5sums_after_list[1]['opt']
                tempmp_vm2 = md5sums_after_list[1][tvaultconf.mount_points[0]]
                if md5sums_list[0]['opt'] != md5sums_after_list[0]['opt'] \
                        and md5sums_list[0]['opt'] == md5sums_after_list[1]['opt']:
                    md5sums_after_list[0]['opt'] = tempopt_vm2
                    md5sums_after_list[1]['opt'] = tempopt_vm1
                if md5sums_list[0][tvaultconf.mount_points[0]] != md5sums_after_list[0][tvaultconf.mount_points[0]] \
                        and md5sums_list[0][tvaultconf.mount_points[0]] == md5sums_after_list[1][
                    tvaultconf.mount_points[0]]:
                    md5sums_after_list[0][tvaultconf.mount_points[0]] = tempmp_vm2
                    md5sums_after_list[1][tvaultconf.mount_points[0]] = tempmp_vm1

        LOG.debug("***MDSUMS*** expected: " + str(md5sums_list) + " actual: " + str(
            md5sums_after_list))

        i = 0
        for each in md5sums_list:
            check_vm = (each == md5sums_after_list[i])
            if check_vm:
                LOG.debug("***MDSUMS MATCH***")
                reporting.add_test_step(
                    "Md5 Verification for VM" + str(i + 1), tvaultconf.PASS)
            else:
                LOG.debug("***MDSUMS DON'T MATCH***")
                reporting.add_test_step(
                    "Md5 Verification for VM" + str(i + 1), tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            i = i + 1

    def _delete_restored_vms(self, restore_id):
        restored_vms = self.get_restored_vm_list(restore_id)
        LOG.debug("Restored vm list : " + str(restored_vms))
        restored_volumes = self.get_restored_volume_list(restore_id)
        LOG.debug("Restored volumes list: {}".format(restored_volumes))
        time.sleep(60)
        # Verify restored instance and volumes are deleted properly.
        try:
            self.delete_restored_vms(restored_vms, restored_volumes)
            LOG.debug("Deleted restored vms and volumes")
        except Exception as e:
            raise Exception(str(e))

    def _selective_restore(self, payload, ip_list, md5sums_list, full=True):
        if full:
            snapshot_id = self.snapshot_id
            snapshot_type = 'full'
        else:
            snapshot_id = self.snapshot_id2
            snapshot_type = 'incremental'
        # Trigger selective restore of snapshot
        restore_id = self.snapshot_selective_restore(
            self.wid, snapshot_id,
            restore_name="selective_restore_" + snapshot_type + "_snap",
            instance_details=payload['instance_details'],
            network_details=payload['network_details'])
        self.wait_for_snapshot_tobe_available(self.wid, snapshot_id)
        if (self.getRestoreStatus(self.wid, snapshot_id,
                                  restore_id) == "available"):
            reporting.add_test_step("Selective restore of " + snapshot_type + " snapshot",
                                    tvaultconf.PASS)
            vm_list = self.get_restored_vm_list(restore_id)
            LOG.debug("Restored vm(selective) ID : " + str(vm_list))
            time.sleep(60)
            i = 0
            for ip in ip_list:
                self.set_floating_ip(ip, vm_list[i])
                i = i + 1
            LOG.debug("Floating ip assigned to selective restored vm -> " + \
                      f"{ip_list}")
            self._check_data_after_restore(ip_list, md5sums_list, 'selective')

            self._delete_restored_vms(restore_id)
        else:
            reporting.add_test_step("Selective restore of " + snapshot_type + " snapshot",
                                    tvaultconf.FAIL)

    def _inplace_restore(self, payload, ip_list, md5sums_list, full=True):
        if full:
            snapshot_id = self.snapshot_id
            snapshot_type = 'full'
        else:
            snapshot_id = self.snapshot_id2
            snapshot_type = 'incremental'

        # Trigger inplace restore of snapshot
        restore_id = self.snapshot_inplace_restore(
            self.wid, snapshot_id, payload)
        self.wait_for_snapshot_tobe_available(self.wid, snapshot_id)
        if (self.getRestoreStatus(self.wid, snapshot_id,
                                  restore_id) == "available"):
            reporting.add_test_step("Inplace restore of " + snapshot_type + " snapshot",
                                    tvaultconf.PASS)
            self._check_data_after_restore(ip_list, md5sums_list, 'inplace')

            restored_volumes = self.get_restored_volume_list(restore_id)
            self.delete_volumes(restored_volumes)
        else:
            reporting.add_test_step("Inplace restore of " + snapshot_type + " snapshot",
                                    tvaultconf.FAIL)

    def _one_click_restore(self, ip_list, md5sums_list, full=True):
        if full:
            snapshot_id = self.snapshot_id
            snapshot_type = 'full'
        else:
            snapshot_id = self.snapshot_id2
            snapshot_type = 'incremental'
        rest_details = {}
        rest_details['rest_type'] = 'oneclick'
        payload = self.create_restore_json(rest_details)
        # Trigger oneclick restore of snapshot
        restore_id = self.snapshot_inplace_restore(
            self.wid, snapshot_id, payload)
        self.wait_for_snapshot_tobe_available(self.wid, snapshot_id)
        if (self.getRestoreStatus(self.wid, snapshot_id,
                                  restore_id) == "available"):
            reporting.add_test_step("Oneclick restore of " + snapshot_type + " snapshot",
                                    tvaultconf.PASS)
            self._check_data_after_restore(ip_list, md5sums_list, 'oneclick')

            self._delete_restored_vms(restore_id)
        else:
            reporting.add_test_step("Oneclick restore of " + snapshot_type + " snapshot",
                                    tvaultconf.FAIL)

    def _check_snapshot_info(self, snapshot_id, num_vms):
        snapshot_info = self.getSnapshotVmVolumeInfo(snapshot_id=snapshot_id)
        if len(snapshot_info.keys()) == num_vms:
            reporting.add_test_step("Number of disk snapshots for multiattach volume VMs is equal to number of Vms",
                                    tvaultconf.PASS)
        else:
            reporting.add_test_step(
                "Number of disk snapshots for multiattach volume VMs is not equal to number of Vms",
                tvaultconf.FAIL)

        vol_flag = True
        for vm in snapshot_info.keys():
            if len(snapshot_info[vm]) != 2:
                vol_flag = False
        if vol_flag:
            reporting.add_test_step("Number of multiattach volume attached to VM is equal to 1", tvaultconf.PASS)
        else:
            reporting.add_test_step("Number of multiattach volume attached to VM is not equal to 1",
                                    tvaultconf.FAIL)

    def _filesearch(self, vms_list, filecount_in_snapshots, search_path):
        for i in range(len(vms_list)):
            filesearch_id = self.filepath_search(vms_list[i], search_path)
            filesearch_status = self.getSearchStatus(filesearch_id)
            if filesearch_status == 'error':
                reporting.add_test_step(f"File search-{i+1} failed", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                snapshot_wise_filecount = self.verifyFilepath_Search(vms_list[i], search_path)

                for snapshot_id in filecount_in_snapshots.keys():
                    if snapshot_wise_filecount[snapshot_id] == \
                            filecount_in_snapshots[snapshot_id]:
                        filesearch_status = True
                    else:
                        filesearch_status = False
                if filesearch_status:
                    reporting.add_test_step(
                        f"Verification of Filesearch-{i+1} with default parameters",
                        tvaultconf.PASS)
                else:
                    LOG.error(f"Filepath Search-{i+1} default_parameters unsuccessful")
                    reporting.add_test_step(
                            f"Verification of Filesearch-{i+1} with default parameters",
                            tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)


    @decorators.attr(type='workloadmgr_api')
    def test_01_multiattach_volumes(self):
        try:
            test_var = "tempest.api.workloadmgr.multiattach_volumes.test_image_booted_"
            tests = [[test_var + "workload_api", 0],
                     [test_var + "full_snapshot_api", 0],
                     [test_var + "incremental_snapshot_api", 0],
                     [test_var + "snapshot_mount_api", 0],
                     [test_var + "filesearch_api", 0],
                     [test_var + "selectiverestore_api", 0],
                     [test_var + "inplacerestore_api", 0],
                     [test_var + "oneclickrestore_api", 0]]
            reporting.add_test_script(tests[0][0])
            self.kp = self.create_key_pair(tvaultconf.key_pair_name)
            self.vm_id_1 = self.create_vm(key_pair=self.kp)
            self.vm_id_2 = self.create_vm(key_pair=self.kp)

            # find volume_type = multiattach. So that existing multiattach volume type can be used.
            # Get the volume_type_id
            vol_type_id = -1
            for vol in CONF.volume.volume_types:
                if (vol.lower().find("multiattach") != -1):
                    vol_type_id = CONF.volume.volume_types[vol]
                    vol_type_name = vol

            if (vol_type_id == -1):
                raise Exception("No multiattach volume found to create multiattach volume. Test cannot be continued")

            # Now create volume with derived volume type id...
            self.volume_id = self.create_volume(
                volume_type_id=vol_type_id, size=6, volume_cleanup=False)

            LOG.debug("Volume ID: " + str(self.volume_id))

            self.volumes = []
            self.volumes.append(self.volume_id)
            # Attach volume to vm...
            api_version.COMPUTE_MICROVERSION = '2.60'
            self.attach_volume(self.volume_id, self.vm_id_1, attach_cleanup=False)
            self.attach_volume(self.volume_id, self.vm_id_2, attach_cleanup=False)
            LOG.debug("Multiattach Volume attached to vm: " + str(self.vm_id_1) + " and " + str(self.vm_id_2))
            api_version.COMPUTE_MICROVERSION = None

            vol_vm_1 = self.get_attached_volumes(self.vm_id_1)
            vol_vm_2 = self.get_attached_volumes(self.vm_id_2)
            LOG.debug("Voulme o VM 1: " + str(vol_vm_1) + " on VM 2:" + str(vol_vm_2))
            if vol_vm_1 == vol_vm_2:
                reporting.add_test_step("Attached Multiattach volume to both Instances", tvaultconf.PASS)
                reporting.set_test_script_status(tvaultconf.PASS)
            else:
                reporting.add_test_step("Attached Multiattach volume to both Instances", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("Multiattach volume failed to attach existing instance")
            fip = self.get_floating_ips()
            LOG.debug("\nAvailable floating ips are {}: \n".format(fip))

            if len(fip) < 7:
                raise Exception("Floating ips unavailable")
            self.set_floating_ip(fip[0], self.vm_id_1)
            self.set_floating_ip(fip[1], self.vm_id_2)

            # Create FRM instance
            self.frm_id = self.create_vm(
                vm_name="file_recovery_manager",
                flavor_id=CONF.compute.flavor_ref_alt,
                user_data=tvaultconf.user_frm_data,
                key_pair=self.kp,
                image_id=list(CONF.compute.fvm_image_ref.values())[0])
            self._set_frm_user()
            LOG.debug("FRM Instance ID: " + str(self.frm_id))
            self.set_floating_ip(fip[6], self.frm_id)

            md5sums_before_full = self._add_data_on_instance_and_volume([fip[0], fip[1]])
            LOG.debug(
                f"md5sums_before_full: {md5sums_before_full}")

            # Create workload with API
            try:
                self.wid = self.workload_create([self.vm_id_1, self.vm_id_2],
                                                tvaultconf.workload_type_id)
                LOG.debug("Workload ID: " + str(self.wid))
            except Exception as e:
                LOG.error(f"Exception: {e}")
                raise Exception("Create workload with image booted vm")
            if (self.wid is not None):
                self.wait_for_workload_tobe_available(self.wid)
                self.workload_status = self.getWorkloadStatus(self.wid)
                if (self.workload_status == "available"):
                    reporting.add_test_step("Create workload with image booted vm", tvaultconf.PASS)
                    tests[0][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Create workload with image booted vm")
            else:
                raise Exception("Create workload with image booted vm")

            reporting.add_test_script(tests[1][0])
            self.snapshot_id = self.workload_snapshot(self.wid, True)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                                                          self.snapshot_id)
            self.mount_path = self.get_mountpoint_path()
            if (self.snapshot_status == "available"):
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                    self.mount_path, self.wid, self.snapshot_id)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                self._check_snapshot_info(self.snapshot_id,2)
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on target backend", tvaultconf.PASS)

                    tests[1][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create full snapshot")

            reporting.add_test_script(tests[2][0])
            md5sums_before_incr = self._add_data_on_instance_and_volume([fip[0], fip[1]], False)
            LOG.debug(
                f"md5sums_before_incr: {md5sums_before_incr}")

            self.snapshot_id2 = self.workload_snapshot(self.wid, False)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                                                          self.snapshot_id2)
            if (self.snapshot_status == "available"):
                reporting.add_test_step("Create incremental snapshot", tvaultconf.PASS)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                    self.mount_path, self.wid, self.snapshot_id2)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                self._check_snapshot_info(self.snapshot_id2,2)
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on target backend", tvaultconf.PASS)

                    tests[2][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create incremental snapshot")

            # Mount snapshot
            reporting.add_test_script(tests[3][0])

            # Mount full snapshot
            self._mount_unmount_snapshot(fip[6])

            # Mount incremental snapshot
            self._mount_unmount_snapshot(fip[6], False)

            reporting.test_case_to_write()
            tests[3][1] = 1

            # File search
            reporting.add_test_script(tests[4][0])
            filecount_in_snapshots = {
                self.snapshot_id: 0,
                self.snapshot_id2: 1}
            search_path = "/opt/File_4"
            vms_list = [self.vm_id_1, self.vm_id_2]
            self._filesearch(vms_list, filecount_in_snapshots, search_path)
            reporting.test_case_to_write()
            tests[4][1] = 1

            # Selective restore
            reporting.add_test_script(tests[5][0])
            rest_details = {}
            rest_details['rest_type'] = 'selective'
            rest_details['volume_type'] = vol_type_name
            rest_details['network_id'] = CONF.network.internal_network_id
            rest_details['subnet_id'] = self.get_subnet_id(
                CONF.network.internal_network_id)
            rest_details['instances'] = {self.vm_id_1: self.volumes, self.vm_id_2: self.volumes}

            payload = self.create_restore_json(rest_details)
            # Trigger selective restore of full snapshot
            self._selective_restore(payload, [fip[2], fip[3]], md5sums_before_full)

            # Trigger selective restore of incremental snapshot
            self._selective_restore(payload, [fip[4], fip[5]], md5sums_before_incr,
                                    False)
            reporting.test_case_to_write()
            tests[5][1] = 1

            # Inplace restore
            reporting.add_test_script(tests[6][0])
            rest_details = {}
            rest_details['rest_type'] = 'inplace'
            rest_details['volume_type'] = vol_type_name
            rest_details['instances'] = {self.vm_id_1: self.volumes, self.vm_id_2: self.volumes}
            payload = self.create_restore_json(rest_details)

            # Trigger inplace restore of full snapshot
            self._inplace_restore(payload, [fip[0], fip[1]], md5sums_before_full)

            # Trigger inplace restore of incremental snapshot
            self._inplace_restore(payload, [fip[0], fip[1]], md5sums_before_incr,
                                  False)

            reporting.test_case_to_write()
            tests[6][1] = 1

            # Oneclick restore
            reporting.add_test_script(tests[7][0])
            self.delete_vm(self.vm_id_1)
            self.delete_vm(self.vm_id_2)
            self.delete_volumes(self.volumes)
            time.sleep(10)

            # Trigger oneclick restore of full snapshot
            self._one_click_restore([fip[0], fip[1]], md5sums_before_full)

            # Trigger oneclick restore of incremental snapshot
            self._one_click_restore([fip[0], fip[1]], md5sums_before_incr, False)
            reporting.test_case_to_write()
            tests[7][1] = 1

        except Exception as e:
            LOG.error(f"Exception: {e}")
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            for test in tests:
                if test[1] != 1:
                    reporting.set_test_script_status(tvaultconf.FAIL)
                    reporting.add_test_script(test[0])
                    reporting.test_case_to_write()


    @decorators.attr(type='workloadmgr_api')
    def test_02_multiattach_volumes(self):
        try:
            test_var = "tempest.api.workloadmgr.multiattach_volumes.test_multiattach_volume_booted_"
            tests = [[test_var + "workload_api", 0],
                     [test_var + "full_snapshot_api", 0],
                     [test_var + "incremental_snapshot_api", 0],
                     [test_var + "selectiverestore_api", 0],
                     [test_var + "inplacerestore_api", 0],
                     [test_var + "oneclickrestore_api", 0]]
            reporting.add_test_script(tests[0][0])
            self.kp = self.create_key_pair(tvaultconf.key_pair_name)

            # find volume_type = multiattach. So that existing multiattach volume type can be used.
            # Get the volume_type_id
            vol_type_id = -1
            for vol in CONF.volume.volume_types:
                if (vol.lower().find("multiattach") != -1):
                    vol_type_id = CONF.volume.volume_types[vol]
                    vol_type_name = vol

            if (vol_type_id == -1):
                raise Exception("No multiattach volume found to create multiattach volume. Test cannot be continued")

            # Now create volume with derived volume type id...
            self.boot_volume_id = self.create_volume(
                volume_type_id=vol_type_id, size=tvaultconf.bootfromvol_vol_size,
                image_id=CONF.compute.image_ref, volume_cleanup=False)
            LOG.debug("Bootable Volume ID: " + str(self.boot_volume_id))
            api_version.COMPUTE_MICROVERSION = '2.60'

            self.volumes = []
            self.volumes.append(self.boot_volume_id)

            self.disk_names = ["vda"]
            self.block_mapping_details = [{"source_type": "volume",
                                           "delete_on_termination": "false",
                                           "boot_index": 0,
                                           "uuid": self.boot_volume_id,
                                           "destination_type": "volume"}]
            self.vm_id = self.create_vm(
                key_pair=self.kp,
                image_id="",
                block_mapping_data=self.block_mapping_details)

            # Now create volume with derived volume type id...
            self.volume_id = self.create_volume(
                volume_type_id=vol_type_id, size=6)

            LOG.debug("Volume ID: " + str(self.volume_id))

            self.volumes.append(self.volume_id)
            # Attach volume to vm...
            self.attach_volume(self.volume_id, self.vm_id)
            LOG.debug("Multiattach Volume attached to vm: " + str(self.vm_id))
            api_version.COMPUTE_MICROVERSION = None

            fip = self.get_floating_ips()
            LOG.debug("\nAvailable floating ips are {}: \n".format(fip))

            if len(fip) < 3:
                raise Exception("Floating ips unavailable")
            self.set_floating_ip(fip[0], self.vm_id)

            md5sums_before_full = self._add_data_on_instance_and_volume([fip[0]])
            LOG.debug(
                f"md5sums_before_full: {md5sums_before_full}")

            # Create workload with API
            try:
                self.wid = self.workload_create([self.vm_id],
                                                tvaultconf.workload_type_id)
                LOG.debug("Workload ID: " + str(self.wid))
            except Exception as e:
                LOG.error(f"Exception: {e}")
                raise Exception("Create workload with volume booted vm")
            if (self.wid is not None):
                self.wait_for_workload_tobe_available(self.wid)
                self.workload_status = self.getWorkloadStatus(self.wid)
                if (self.workload_status == "available"):
                    reporting.add_test_step("Create workload with volume booted vm", tvaultconf.PASS)
                    tests[0][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Create workload with volume booted vm")
            else:
                raise Exception("Create workload with volume booted vm")

            reporting.add_test_script(tests[1][0])
            self.snapshot_id = self.workload_snapshot(self.wid, True)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                                                          self.snapshot_id)
            self.mount_path = self.get_mountpoint_path()
            if (self.snapshot_status == "available"):
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                    self.mount_path, self.wid, self.snapshot_id)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on target backend", tvaultconf.PASS)

                    tests[1][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create full snapshot")

            reporting.add_test_script(tests[2][0])
            md5sums_before_incr = self._add_data_on_instance_and_volume([fip[0]], False)
            LOG.debug(
                f"md5sums_before_incr: {md5sums_before_incr}")

            self.snapshot_id2 = self.workload_snapshot(self.wid, False)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                                                          self.snapshot_id2)
            if (self.snapshot_status == "available"):
                reporting.add_test_step("Create incremental snapshot", tvaultconf.PASS)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                    self.mount_path, self.wid, self.snapshot_id2)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on target backend", tvaultconf.PASS)

                    tests[2][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create incremental snapshot")

            # Selective restore
            reporting.add_test_script(tests[3][0])
            rest_details = {}
            rest_details['rest_type'] = 'selective'
            rest_details['volume_type'] = vol_type_name
            rest_details['network_id'] = CONF.network.internal_network_id
            rest_details['subnet_id'] = self.get_subnet_id(
                CONF.network.internal_network_id)
            rest_details['instances'] = {self.vm_id: self.volumes}

            payload = self.create_restore_json(rest_details)
            # Trigger selective restore of full snapshot
            self._selective_restore(payload, [fip[1]], md5sums_before_full)

            # Trigger selective restore of incremental snapshot
            self._selective_restore(payload, [fip[2]], md5sums_before_incr,
                                    False)
            reporting.test_case_to_write()
            tests[3][1] = 1

            # Inplace restore
            reporting.add_test_script(tests[4][0])
            rest_details = {}
            rest_details['rest_type'] = 'inplace'
            rest_details['volume_type'] = vol_type_name
            rest_details['instances'] = {self.vm_id: self.volumes}
            payload = self.create_restore_json(rest_details)

            # Trigger inplace restore of full snapshot
            self._inplace_restore(payload, [fip[0]], md5sums_before_full)

            # Trigger inplace restore of incremental snapshot
            self._inplace_restore(payload, [fip[0]], md5sums_before_incr,
                                  False)

            reporting.test_case_to_write()
            tests[4][1] = 1

            # Oneclick restore
            reporting.add_test_script(tests[5][0])
            self.delete_vm(self.vm_id)
            self.delete_volumes(self.volumes)
            time.sleep(10)

            # Trigger oneclick restore of full snapshot
            self._one_click_restore([fip[0]], md5sums_before_full)

            # Trigger oneclick restore of incremental snapshot
            self._one_click_restore([fip[0]], md5sums_before_incr, False)
            reporting.test_case_to_write()
            tests[5][1] = 1


        except Exception as e:
            LOG.error(f"Exception: {e}")
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            for test in tests:
                if test[1] != 1:
                    reporting.set_test_script_status(tvaultconf.FAIL)
                    reporting.add_test_script(test[0])
                    reporting.test_case_to_write()

    # Workload with scheduler and retention parameter
    @decorators.attr(type='workloadmgr_cli')
    def test_03_multiattach(self):
        reporting.add_test_script(str(__name__) + "_retention_with_multiattach_volume")
        try:
            self.vm_id_1 = self.create_vm()
            self.vm_id_2 = self.create_vm()

            # find volume_type = multiattach. So that existing multiattach volume type can be used.
            # Get the volume_type_id
            vol_type_id = -1
            for vol in CONF.volume.volume_types:
                if (vol.lower().find("multiattach") != -1):
                    vol_type_id = CONF.volume.volume_types[vol]
                    vol_type_name = vol

            if (vol_type_id == -1):
                raise Exception(
                    "No multiattach volume found to create multiattach volume. Test cannot be continued")

            # Now create volume with derived volume type id...
            self.volume_id = self.create_volume(
                volume_type_id=vol_type_id, size=2, volume_cleanup=False)

            LOG.debug("Volume ID: " + str(self.volume_id))

            self.volumes = []
            self.volumes.append(self.volume_id)
            # Attach volume to vm...
            api_version.COMPUTE_MICROVERSION = '2.60'
            self.attach_volume(self.volume_id, self.vm_id_1, attach_cleanup=False)
            self.attach_volume(self.volume_id, self.vm_id_2, attach_cleanup=False)
            LOG.debug("Multiattach Volume attached to vm: " + str(self.vm_id_1) + " and " + str(self.vm_id_2))
            api_version.COMPUTE_MICROVERSION = None

            vol_vm_1 = self.get_attached_volumes(self.vm_id_1)
            vol_vm_2 = self.get_attached_volumes(self.vm_id_2)
            LOG.debug("Voulme o VM 1: " + str(vol_vm_1) + " on VM 2:" + str(vol_vm_2))
            if vol_vm_1 == vol_vm_2:
                reporting.add_test_step("Attached Multiattach volume to both Instances", tvaultconf.PASS)
                reporting.set_test_script_status(tvaultconf.PASS)
            else:
                reporting.add_test_step("Attached Multiattach volume to both Instances", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("Multiattach volume failed to attach existing instance")

            retention = int(tvaultconf.retention_policy_value)
            start_date = time.strftime("%m/%d/%Y")
            start_time = (datetime.now() + timedelta(minutes=5)
                          ).strftime("%I:%M %p")
            self.schedule = {
                "fullbackup_interval": "0",
                "retention_policy_type": tvaultconf.retention_policy_type,
                "interval": tvaultconf.interval,
                "enabled": True,
                "start_date": start_date,
                "start_time": start_time,
                "retention_policy_value": retention}

            # Create workload with API
            try:
                self.wid = self.workload_create([self.vm_id_1, self.vm_id_2],
                                                workload_type=tvaultconf.parallel,
                                                jobschedule=self.schedule,
                                                workload_name='Workload-1',
                                                description='New Test')
                LOG.debug("Workload ID: " + str(self.wid))
            except Exception as e:
                LOG.error(f"Exception: {e}")
                raise Exception("Create workload with image booted vm")
            if (self.wid is not None):
                self.wait_for_workload_tobe_available(self.wid)
                self.workload_status = self.getWorkloadStatus(self.wid)
                if (self.workload_status == "available"):
                    reporting.add_test_step("Create workload", tvaultconf.PASS)
                else:
                    raise Exception("Create workload failed")
            else:
                raise Exception("Create workload failed")

            for num in range(retention+1):
                snapshot_name = 'Tempest-retention-snapshot' + str(num + 1)
                self.snapshot_id = self.workload_snapshot(self.wid, True, snapshot_name=snapshot_name)
                self.wait_for_workload_tobe_available(self.wid)

            snapshots = self.getSnapshotList(workload_id=self.wid)
            snapshots1 = [x for x in snapshots if self.getSnapshotStatus(
                self.wid, x) == 'available']
            snapshot1 = [x1 for x1 in snapshots1 if self.getSnapshotInfo(
                snapshot_id=x1)[1] == 'Tempest-retention-snapshot1']

            if len(snapshots1) == retention and len(snapshot1) == 0:
                LOG.debug("Retention passed")
                reporting.add_test_step("Retention of snapshots for multiattach volume VM", tvaultconf.PASS)
            else:
                LOG.debug("Retention failed")
                reporting.add_test_step("Retention of snapshots for multiattach volume VM", tvaultconf.FAIL)
                raise Exception("Retention failed")
            reporting.test_case_to_write()

            reporting.add_test_script(str(__name__) + "_scheduler_with_multiattach_volume")
            # Verify workload created with scheduler enable
            status = self.getSchedulerStatus(self.wid)
            if status:
                reporting.add_test_step(
                    "Verify workload created with scheduler enabled",
                    tvaultconf.PASS)
                LOG.debug("Workload created with scheduler enabled successfully")
            else:
                reporting.add_test_step(
                    "Verify workload created with scheduler enabled",
                    tvaultconf.FAIL)
                raise Exception(
                    "Workload has not been created with scheduler enabled")
            reporting.test_case_to_write()

            reporting.add_test_script(str(__name__) + "_workload_reset_with_multiattach_volume")
            workload_reset_status = self.workload_reset(self.wid)
            if workload_reset_status:
                reporting.add_test_step("Workload reset request raised", tvaultconf.PASS)
            else:
                LOG.error("Workload reset request failed")
                reporting.add_test_step("Workload reset request failed", tvaultconf.FAIL)
                raise Exception("Workload reset request failed")

            start_time = time.time()
            time.sleep(10)
            volsnaps_after = self.get_volume_snapshots(self.volume_id)
            while (len(volsnaps_after) != 0 and (time.time() - start_time < 600)):
                volsnaps_after = self.get_volume_snapshots(self.volume_id)
                time.sleep(5)
            if len(volsnaps_after) == 0:
                reporting.add_test_step("Temp Volume snapshot is deleted after workload reset", tvaultconf.PASS)
            else:
                reporting.add_test_step("Temp Volume snapshot not deleted after workload reset", tvaultconf.FAIL)
                raise Exception("Workload reset failed as temp volume snapshot is not deleted")
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_04_multiattach(self):
        reporting.add_test_script(str(__name__) + "_snapshot_multiattach_volume_with_multiple_workloads")
        try:
            self.kp = self.create_key_pair(tvaultconf.key_pair_name)
            self.vm_id_1 = self.create_vm(key_pair=self.kp)
            self.vm_id_2 = self.create_vm(key_pair=self.kp)

            # find volume_type = multiattach. So that existing multiattach volume type can be used.
            # Get the volume_type_id
            vol_type_id = -1
            for vol in CONF.volume.volume_types:
                if (vol.lower().find("multiattach") != -1):
                    vol_type_id = CONF.volume.volume_types[vol]
                    vol_type_name = vol

            if (vol_type_id == -1):
                raise Exception("No multiattach volume found to create multiattach volume. Test cannot be continued")

            # Now create volume with derived volume type id...
            self.volume_id = self.create_volume(
                volume_type_id=vol_type_id, size=6, volume_cleanup=False)

            LOG.debug("Volume ID: " + str(self.volume_id))

            self.volumes = []
            self.volumes.append(self.volume_id)
            # Attach volume to vm...
            api_version.COMPUTE_MICROVERSION = '2.60'
            self.attach_volume(self.volume_id, self.vm_id_1, attach_cleanup=False)
            self.attach_volume(self.volume_id, self.vm_id_2, attach_cleanup=False)
            LOG.debug("Multiattach Volume attached to vm: " + str(self.vm_id_1) + " and " + str(self.vm_id_2))
            api_version.COMPUTE_MICROVERSION = None

            vol_vm_1 = self.get_attached_volumes(self.vm_id_1)
            vol_vm_2 = self.get_attached_volumes(self.vm_id_2)
            LOG.debug("Voulme o VM 1: " + str(vol_vm_1) + " on VM 2:" + str(vol_vm_2))
            if vol_vm_1 == vol_vm_2:
                reporting.add_test_step("Attached Multiattach volume to both Instances", tvaultconf.PASS)
                reporting.set_test_script_status(tvaultconf.PASS)
            else:
                reporting.add_test_step("Attached Multiattach volume to both Instances", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("Multiattach volume failed to attach existing instance")
            fip = self.get_floating_ips()
            LOG.debug("\nAvailable floating ips are {}: \n".format(fip))

            if len(fip) < 2:
                raise Exception("Floating ips unavailable")
            self.set_floating_ip(fip[0], self.vm_id_1)
            self.set_floating_ip(fip[1], self.vm_id_2)


            md5sums_before_full = self._add_data_on_instance_and_volume([fip[0], fip[1]])
            LOG.debug(
                f"md5sums_before_full: {md5sums_before_full}")

            # Create workload with API
            try:
                wid1 = self.workload_create([self.vm_id_1],
                                                tvaultconf.workload_type_id)
                LOG.debug("Workload ID1 : " + str(wid1))
                wid2 = self.workload_create([self.vm_id_2],
                                            tvaultconf.workload_type_id)
                LOG.debug("Workload ID2 : " + str(wid2))

            except Exception as e:
                LOG.error(f"Exception: {e}")
                raise Exception("Create multiple workloads with image booted vm")

            if (wid1 is not None and wid2 is not None):
                self.wait_for_workload_tobe_available(wid1)
                self.wait_for_workload_tobe_available(wid2)

                workload_status1 = self.getWorkloadStatus(wid1)
                workload_status2 = self.getWorkloadStatus(wid2)

                if (workload_status1 == "available" and workload_status2 == "available"):
                    reporting.add_test_step("Create multi[ple workloads with image booted vm", tvaultconf.PASS)
                else:
                    raise Exception("Create multiple workloads with image booted vm")
            else:
                raise Exception("Create multiple workloads with image booted vm")

            snapshot_id1 = self.workload_snapshot(wid1, True)
            snapshot_id2 = self.workload_snapshot(wid2, True)

            self.wait_for_workload_tobe_available(wid1)
            self.wait_for_workload_tobe_available(wid2)

            snapshot_status1 = self.getSnapshotStatus(wid1,snapshot_id1)
            snapshot_status2 = self.getSnapshotStatus(wid2,snapshot_id2)
            mount_path = self.get_mountpoint_path()

            if (snapshot_status1 == "available" and snapshot_status2 == "available"):
                reporting.add_test_step("Create multiple full snapshots on multiple workloads", tvaultconf.PASS)
                snapshot_found1 = self.check_snapshot_exist_on_backend(mount_path, wid1, snapshot_id1)
                LOG.debug(f"snapshot_found1: {snapshot_found1}")
                self._check_snapshot_info(snapshot_id1,1)
                snapshot_found2 = self.check_snapshot_exist_on_backend(mount_path, wid2, snapshot_id2)
                LOG.debug(f"snapshot_found2: {snapshot_found2}")
                self._check_snapshot_info(snapshot_id2,1)

                if snapshot_found1 and snapshot_found2:
                    reporting.add_test_step("Verify multiple snapshots existence on target backend", tvaultconf.PASS)
                else:
                    raise Exception("Verify multiple snapshots existence on target backend")
            else:
                raise Exception("Create multiple full snapshots on multiple workloads")

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

