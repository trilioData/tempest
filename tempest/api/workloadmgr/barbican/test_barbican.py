from tempest.api.workloadmgr import base
from tempest import config
from tempest.lib import decorators
import time
from oslo_log import log as logging
from tempest import tvaultconf
from tempest import reporting
#from tempest import command_argument_string
#from tempest.util import cli_parser
#from tempest.util import query_data

LOG = logging.getLogger(__name__)
CONF = config.CONF

class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()

    @decorators.attr(type='workloadmgr_api')
    def test_1_barbican(self):
        try:
            test_var = "tempest.api.workloadmgr.barbican.test_image_booted_"
            tests = [[test_var+"workload_api", 0],
                    [test_var+"full_snapshot_api", 0],
                    [test_var+"incremental_snapshot_api", 0],
                    [test_var+"snapshot_mount_api", 0],
                    [test_var+"filesearch_api", 0],
                    [test_var+"selectiverestore_api", 0],
                    [test_var+"inplacerestore_api", 0],
                    [test_var+"oneclickrestore_api", 0]]
            reporting.add_test_script(tests[0][0])
            self.kp = self.create_key_pair(tvaultconf.key_pair_name)
            self.vm_id = self.create_vm(key_pair=self.kp)
            self.volumes = []
            fip = self.get_floating_ips()
            LOG.debug("\nAvailable floating ips are {}: \n".format(fip))
            if len(fip) < 4:
                raise Exception("Floating ips unavailable")
            self.set_floating_ip(fip[0], self.vm_id)

            self.frm_id = self.create_vm(
                vm_name="file_recovery_manager",
                flavor_id=CONF.compute.flavor_ref_alt,
                user_data=tvaultconf.user_frm_data,
                key_pair=self.kp,
                image_id=list(CONF.compute.fvm_image_ref.values())[0])
            LOG.debug("FRM Instance ID: " + str(self.frm_id))
            self.set_floating_ip(fip[1], self.frm_id)

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            stdin, stdout, stderr = ssh.exec_command("sudo apt install qemu-guest-agent")
            self.addCustomfilesOnLinuxVM(ssh, "/root", 3)
            md5sums_before_full = self.calculatemmd5checksum(ssh, "/root")
            LOG.debug(f"md5sums_before_full: {md5sums_before_full}")
            ssh.close()
            self.secret_uuid = self.create_secret()

            # Create workload with API
            try:
                self.wid = self.workload_create([self.vm_id],
                        tvaultconf.workload_type_id, encryption=True,
                        secret_uuid=self.secret_uuid)
                LOG.debug("Workload ID: " + str(self.wid))
            except Exception as e:
                LOG.error(f"Exception: {e}")
                raise Exception("Create encrypted workload "\
                        "with image booted vm")
            if(self.wid is not None):
                self.wait_for_workload_tobe_available(self.wid)
                self.workload_status = self.getWorkloadStatus(self.wid)
                if(self.workload_status == "available"):
                    reporting.add_test_step("Create encrypted workload "\
                            "with image booted vm", tvaultconf.PASS)
                    tests[0][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Create encrypted workload "\
                         "with image booted vm")
            else:
                raise Exception("Create encrypted workload with image "\
                        "booted vm")

            reporting.add_test_script(tests[1][0])
            self.snapshot_id = self.workload_snapshot(self.wid, True)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id)
            if(self.snapshot_status == "available"):
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                self.mount_path = self.get_mountpoint_path(
                        tvaultconf.tvault_ip[0], tvaultconf.tvault_username,
                        tvaultconf.tvault_password)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                        tvaultconf.tvault_ip[0], tvaultconf.tvault_username,
                        tvaultconf.tvault_password, self.mount_path,
                        self.wid, self.snapshot_id)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on "\
                            "target backend", tvaultconf.PASS)
                    tests[1][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create full snapshot")

            reporting.add_test_script(tests[2][0])
            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.addCustomfilesOnLinuxVM(ssh, "/root", 5)
            md5sums_before_incr = self.calculatemmd5checksum(ssh, "/root")
            LOG.debug(f"md5sums_before_incr: {md5sums_before_incr}")
            ssh.close()

            self.snapshot_id2 = self.workload_snapshot(self.wid, False)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id2)
            if(self.snapshot_status == "available"):
                reporting.add_test_step("Create incremental snapshot", tvaultconf.PASS)
                self.mount_path = self.get_mountpoint_path(
                        tvaultconf.tvault_ip[0], tvaultconf.tvault_username,
                        tvaultconf.tvault_password)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                        tvaultconf.tvault_ip[0], tvaultconf.tvault_username,
                        tvaultconf.tvault_password, self.mount_path,
                        self.wid, self.snapshot_id2)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on "\
                            "target backend", tvaultconf.PASS)
                    tests[2][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create incremental snapshot")
                #reporting.add_test_step("Create incremental snapshot", tvaultconf.FAIL)
                #reporting.set_test_script_status(tvaultconf.FAIL)

            reporting.add_test_script(tests[3][0])
            # Mount full snapshot
            mount_status = self.mount_snapshot(
                self.wid, self.snapshot_id, self.frm_id)
            LOG.debug(f"mount_status for full snapshot: {mount_status}")
            if mount_status:
                reporting.add_test_step(
                    "Snapshot mount of full snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1],CONF.validation.fvm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh).decode('UTF-8').split('\n')
                ssh.close()
                flag = 0
                for i in output_list:
                    if 'vda1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that mountpoint mounted is shown on FVM instance",
                            tvaultconf.PASS)
                        flag = 1
                        if 'File_1' in i:
                            reporting.add_test_step(
                                "Verification of file's existance on mounted snapshot",
                                tvaultconf.PASS)
                        else:
                            reporting.add_test_step(
                                "Verification of file's existance on mounted snapshot",
                                tvaultconf.FAIL)
                    else:
                        pass

                if flag == 0:
                    reporting.add_test_step(
                        "Verify that mountpoint mounted is shown on FVM instance",
                        tvaultconf.FAIL)
                else:
                    pass

            unmount_status = self.unmount_snapshot(self.wid, self.snapshot_id)
            LOG.debug("VALUE OF is_unmounted: " + str(unmount_status))
            if unmount_status:
                reporting.add_test_step(
                   "Snapshot unmount of full snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                    fip[1], CONF.validation.fvm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh)
                ssh.close()

                if output_list == b'':
                    reporting.add_test_step(
                        "Unmount full snapshot", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                            "Snapshot unmount of full snapshot", tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Snapshot unmount of full snapshot", tvaultconf.FAIL)

            # Mount incremental snapshot
            mount_status = self.mount_snapshot(
                self.wid, self.snapshot_id2, self.frm_id)
            if mount_status:
                reporting.add_test_step(
                    "Snapshot mount of incremental snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1],CONF.validation.fvm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh,
                        file_name="File_5").decode('UTF-8').split('\n')
                ssh.close()
                flag = 0
                for i in output_list:
                    if 'vda1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that mountpoint mounted is shown on FVM instance",
                            tvaultconf.PASS)
                        flag = 1
                        if 'File_5' in i:
                            reporting.add_test_step(
                                "Verification of file's existance on mounted snapshot",
                                tvaultconf.PASS)
                        else:
                            reporting.add_test_step(
                                "Verification of file's existance on mounted snapshot",
                                tvaultconf.FAIL)
                    else:
                        pass

                if flag == 0:
                    reporting.add_test_step(
                        "Verify that mountpoint mounted is shown on FVM instance",
                        tvaultconf.FAIL)
                else:
                    pass

            unmount_status = self.unmount_snapshot(self.wid, self.snapshot_id2)
            LOG.debug("VALUE OF is_unmounted: " + str(unmount_status))
            if unmount_status:
                reporting.add_test_step(
                    "Snapshot unmount of incremental snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1], CONF.validation.fvm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh)
                ssh.close()

                if output_list == b'':
                    reporting.add_test_step(
                        "Unmount incremental snapshot", tvaultconf.PASS)
                    tests[3][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception(
                        "Snapshot unmount of incremental snapshot")
            else:
                raise Exception(
                    "Snapshot unmount of incremental snapshot")

            #File search
            reporting.add_test_script(tests[4][0])
            filecount_in_snapshots = {
                self.snapshot_id: 0,
                self.snapshot_id2: 1}
            filesearch_id = self.filepath_search(
                self.vm_id, "/root/File_4")
            snapshot_wise_filecount = self.verifyFilepath_Search(
                filesearch_id, "/root/File_4")
            for snapshot_id in filecount_in_snapshots.keys():
                if snapshot_wise_filecount[snapshot_id] == filecount_in_snapshots[snapshot_id]:
                    filesearch_status = True
                else:
                    filesearch_status = False

            if filesearch_status:
                LOG.debug("Filepath_Search default_parameters successful")
                reporting.add_test_step(
                    "Verification of Filesearch with default parameters",
                    tvaultconf.PASS)
                tests[4][1] = 1
            else:
                LOG.debug("Filepath Search default_parameters unsuccessful")
                reporting.add_test_step(
                        "Verification of Filesearch with default parameters",
                        tvaultconf.FAIL)
            reporting.test_case_to_write()
            tests[4][1] = 1

            #selective restore
            reporting.add_test_script(tests[5][0])
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
                self.set_floating_ip(fip[2], vm_list[0])
                LOG.debug("Floating ip assigned to selective restored vm -> " +\
                        f"{fip[2]}")
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[2])
                md5sums_after_full_selective = self.calculatemmd5checksum(ssh, "/root")
                LOG.debug(f"md5sums_after_full_selective: {md5sums_after_full_selective}")
                ssh.close()

                if md5sums_before_full == \
                        md5sums_after_full_selective:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Selective restore of full snapshot",
                        tvaultconf.FAIL)

            # Trigger selective restore of incremental snapshot
            restore_id_2 = self.snapshot_selective_restore(
                self.wid, self.snapshot_id2,
                restore_name="selective_restore_full_snap",
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
                self.set_floating_ip(fip[3], vm_list[0])
                LOG.debug("Floating ip assigned to selective restored vm -> " +\
                        f"{fip[3]}")
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[3])
                md5sums_after_incr_selective = self.calculatemmd5checksum(ssh, "/root")
                LOG.debug(f"md5sums_after_incr_selective: {md5sums_after_incr_selective}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_selective:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
                    tests[5][1] = 1
                    reporting.test_case_to_write()
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Selective restore of incremental snapshot",
                        tvaultconf.FAIL)
            reporting.test_case_to_write()
            tests[5][1] = 1

            #Inplace restore for full snapshot
            reporting.add_test_script(tests[6][0])
            rest_details = {}
            rest_details['rest_type'] = 'inplace'
            rest_details['instances'] = {self.vm_id: self.volumes}
            payload = self.create_restore_json(rest_details)
            # Trigger inplace restore of full snapshot
            restore_id_3 = self.snapshot_inplace_restore(
                self.wid, self.snapshot_id, payload)
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id)
            if(self.getRestoreStatus(self.wid, self.snapshot_id,
                    restore_id_3) == "available"):
                reporting.add_test_step("Inplace restore of full snapshot",
                        tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                md5sums_after_full_inplace = self.calculatemmd5checksum(ssh, "/root")
                LOG.debug(f"md5sums_after_full_inplace: {md5sums_after_full_inplace}")
                ssh.close()

                if md5sums_before_full == \
                        md5sums_after_full_inplace:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Inplace restore of full snapshot",
                        tvaultconf.FAIL)

            # Trigger inplace restore of incremental snapshot
            restore_id_4 = self.snapshot_inplace_restore(
                self.wid, self.snapshot_id2, payload)
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id2)
            if(self.getRestoreStatus(self.wid, self.snapshot_id2,
                    restore_id_4) == "available"):
                reporting.add_test_step("Inplace restore of incremental snapshot",
                        tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                md5sums_after_incr_inplace = self.calculatemmd5checksum(ssh, "/root")
                LOG.debug(f"md5sums_after_incr_inplace: {md5sums_after_incr_inplace}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_inplace:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
                    tests[6][1] = 1
                    reporting.test_case_to_write()
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Inplace restore of incremental snapshot",
                        tvaultconf.FAIL)
            reporting.test_case_to_write()
            tests[6][1] = 1

            reporting.add_test_script(tests[7][0])
            self.delete_vm(self.vm_id)
            time.sleep(10)
            rest_details = {}
            rest_details['rest_type'] = 'oneclick'
            payload = self.create_restore_json(rest_details)
            # Trigger oneclick restore of full snapshot
            restore_id_5 = self.snapshot_inplace_restore(
                self.wid, self.snapshot_id, payload)
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id)
            if(self.getRestoreStatus(self.wid, self.snapshot_id,
                    restore_id_5) == "available"):
                reporting.add_test_step("Oneclick restore of full snapshot",
                        tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                md5sums_after_full_oneclick = self.calculatemmd5checksum(ssh, "/root")
                LOG.debug(f"md5sums_after_full_oneclick: {md5sums_after_full_oneclick}")
                ssh.close()

                if md5sums_before_full == \
                        md5sums_after_full_oneclick:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Oneclick restore of full snapshot",
                        tvaultconf.FAIL)

            vm_list = self.get_restored_vm_list(restore_id_5)
            LOG.debug(f"vm_list: {vm_list}, self.vm_id: {self.vm_id}")
            self.delete_vm(vm_list[0])
            time.sleep(5)
            rest_details = {}
            rest_details['rest_type'] = 'oneclick'
            payload = self.create_restore_json(rest_details)
            # Trigger oneclick restore of incremental snapshot
            restore_id_6 = self.snapshot_inplace_restore(
                self.wid, self.snapshot_id2, payload)
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id2)
            if(self.getRestoreStatus(self.wid, self.snapshot_id2,
                    restore_id_6) == "available"):
                reporting.add_test_step("Oneclick restore of incremental snapshot",
                        tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                md5sums_after_incr_oneclick = self.calculatemmd5checksum(ssh, "/root")
                LOG.debug(f"md5sums_after_incr_oneclick: {md5sums_after_incr_oneclick}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_oneclick:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
                    tests[7][1] = 1
                    reporting.test_case_to_write()
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Oneclick restore of incremental snapshot",
                        tvaultconf.FAIL)

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
    def test_2_barbican(self):
        try:
            test_var = "tempest.api.workloadmgr.barbican.test_image_boot_vol_attach_"
            tests = [[test_var+"workload_api", 0],
                    [test_var+"full_snapshot_api", 0],
                    [test_var+"incremental_snapshot_api", 0],
                    [test_var+"snapshot_mount_api", 0],
                    [test_var+"filesearch_api", 0],
                    [test_var+"selectiverestore_api", 0],
                    [test_var+"inplacerestore_api", 0],
                    [test_var+"oneclickrestore_api", 0]]
            reporting.add_test_script(tests[0][0])
            self.kp = self.create_key_pair(tvaultconf.key_pair_name)
            self.vm_id = self.create_vm(key_pair=self.kp)
            fip = self.get_floating_ips()
            LOG.debug("\nAvailable floating ips are {}: \n".format(fip))
            if len(fip) < 4:
                raise Exception("Floating ips unavailable")
            self.set_floating_ip(fip[0], self.vm_id)
            self.volumes = []
            for i in range(2):
                self.volume_id = self.create_volume(
                        volume_type_id=CONF.volume.volume_type_id)
                self.volumes.append(self.volume_id)
                self.attach_volume(self.volume_id, self.vm_id)
            LOG.debug(f"Volumes attached: {self.volumes}")

            self.secret_uuid = self.create_secret()
            self.frm_id = self.create_vm(
                vm_name="file_recovery_manager",
                flavor_id=CONF.compute.flavor_ref_alt,
                user_data=tvaultconf.user_frm_data,
                key_pair=self.kp,
                image_id=list(CONF.compute.fvm_image_ref.values())[0])
            LOG.debug("FRM Instance ID: " + str(self.frm_id))
            self.set_floating_ip(fip[1], self.frm_id)

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            stdin, stdout, stderr = ssh.exec_command("sudo apt install qemu-guest-agent")
            self.addCustomfilesOnLinuxVM(ssh, "/root", 3)
            self.execute_command_disk_create(ssh, fip[0],
                    tvaultconf.volumes_parts, tvaultconf.mount_points)
            self.execute_command_disk_mount(ssh, fip[0],
                    tvaultconf.volumes_parts, tvaultconf.mount_points)
            for mp in tvaultconf.mount_points:
                self.addCustomfilesOnLinuxVM(ssh, mp, 4)

            md5sums_before_full = {}
            md5sums_before_full['root'] = self.calculatemmd5checksum(ssh, "/root")
            for mp in tvaultconf.mount_points:
                md5sums_before_full[mp] = self.calculatemmd5checksum(ssh, mp)
            LOG.debug(f"md5sums_before_full: {md5sums_before_full}")
            ssh.close()

            # Create workload with API
            try:
                self.wid = self.workload_create([self.vm_id],
                        tvaultconf.workload_type_id, encryption=True,
                        secret_uuid=self.secret_uuid)
                LOG.debug("Workload ID: " + str(self.wid))
            except Exception as e:
                LOG.error(f"Exception: {e}")
                raise Exception("Create encrypted workload "\
                        "with image booted vm and vol attached")
            if(self.wid is not None):
                self.wait_for_workload_tobe_available(self.wid)
                self.workload_status = self.getWorkloadStatus(self.wid)
                if(self.workload_status == "available"):
                    reporting.add_test_step("Create encrypted workload "\
                            "with image booted vm and vol attached",
                            tvaultconf.PASS)
                    tests[0][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Create encrypted workload "\
                         "with image booted vm and vol attached")
            else:
                raise Exception("Create encrypted workload with image "\
                        "booted vm and vol attached")

            reporting.add_test_script(tests[1][0])
            self.snapshot_id = self.workload_snapshot(self.wid, True)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id)
            if(self.snapshot_status == "available"):
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                self.mount_path = self.get_mountpoint_path(
                        tvaultconf.tvault_ip[0], tvaultconf.tvault_username,
                        tvaultconf.tvault_password)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                        tvaultconf.tvault_ip[0], tvaultconf.tvault_username,
                        tvaultconf.tvault_password, self.mount_path,
                        self.wid, self.snapshot_id)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on "\
                            "target backend", tvaultconf.PASS)
                    tests[1][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create full snapshot")

            reporting.add_test_script(tests[2][0])
            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.addCustomfilesOnLinuxVM(ssh, "/root", 6)
            md5sums_before_incr = {}
            md5sums_before_incr['root'] = self.calculatemmd5checksum(ssh, "/root")
            for mp in tvaultconf.mount_points:
                self.addCustomfilesOnLinuxVM(ssh, mp, 6)
                md5sums_before_incr[mp] = self.calculatemmd5checksum(ssh, mp)
            LOG.debug(f"md5sums_before_incr: {md5sums_before_incr}")
            ssh.close()

            self.snapshot_id2 = self.workload_snapshot(self.wid, False)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id2)
            if(self.snapshot_status == "available"):
                reporting.add_test_step("Create incremental snapshot", tvaultconf.PASS)
                self.mount_path = self.get_mountpoint_path(
                        tvaultconf.tvault_ip[0], tvaultconf.tvault_username,
                        tvaultconf.tvault_password)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                        tvaultconf.tvault_ip[0], tvaultconf.tvault_username,
                        tvaultconf.tvault_password, self.mount_path,
                        self.wid, self.snapshot_id2)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on "\
                            "target backend", tvaultconf.PASS)
                    tests[2][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create incremental snapshot")

            reporting.add_test_script(tests[3][0])
            # Mount full snapshot
            mount_status = self.mount_snapshot(
                self.wid, self.snapshot_id, self.frm_id)
            LOG.debug(f"mount_status for full snapshot: {mount_status}")
            if mount_status:
                reporting.add_test_step(
                    "Snapshot mount of full snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1],CONF.validation.fvm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh,
                        file_name="File_2").decode('UTF-8').split('\n')
                ssh.close()
                flag = {'root': 0, 'vdb': 0, 'vdc': 0}
                for i in output_list:
                    if 'vda1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that bootdisk mounted is shown on FVM "\
                                    "instance", tvaultconf.PASS)
                        flag['root'] = 1
                        if 'File_2' in i:
                            reporting.add_test_step(
                                "Verification of bootdisk file's existance "\
                                        "on mounted snapshot", tvaultconf.PASS)
                        else:
                            reporting.add_test_step(
                                "Verification of bootdisk file's existance on"\
                                        " mounted snapshot", tvaultconf.FAIL)
                    if 'vdb1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that volume1 mounted is shown on FVM "\
                                    "instance", tvaultconf.PASS)
                        flag['vdb'] = 1
                        if 'File_2' in i:
                            reporting.add_test_step(
                                "Verification of volume1 file's existance "\
                                        "on mounted snapshot", tvaultconf.PASS)
                        else:
                            reporting.add_test_step(
                                "Verification of volume1 file's existance "\
                                        "on mounted snapshot", tvaultconf.FAIL)
                    if 'vdc1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that volume2 mounted is shown on FVM "\
                                    "instance", tvaultconf.PASS)
                        flag['vdc'] = 1
                        if 'File_2' in i:
                            reporting.add_test_step(
                                "Verification of volume2 file's existance "\
                                        "on mounted snapshot", tvaultconf.PASS)
                        else:
                            reporting.add_test_step(
                                "Verification of volume2 file's existance "\
                                        "on mounted snapshot", tvaultconf.FAIL)
                for k,v in flag.items():
                    if v == 0:
                        reporting.add_test_step("Verify that mountpoint "\
                                "mounted is shown on FVM instance",
                                tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Snapshot mount of full snapshot", tvaultconf.FAIL)

            unmount_status = self.unmount_snapshot(self.wid, self.snapshot_id)
            LOG.debug("VALUE OF is_unmounted: " + str(unmount_status))
            if unmount_status:
                reporting.add_test_step(
                   "Snapshot unmount of full snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                    fip[1], CONF.validation.fvm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh)
                ssh.close()

                if output_list == b'':
                    reporting.add_test_step(
                        "Unmount full snapshot", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                            "Snapshot unmount of full snapshot", tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Snapshot unmount of full snapshot", tvaultconf.FAIL)

            # Mount incremental snapshot
            mount_status = self.mount_snapshot(
                self.wid, self.snapshot_id2, self.frm_id)
            if mount_status:
                reporting.add_test_step(
                    "Snapshot mount of incremental snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1],CONF.validation.fvm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh,
                        file_name="File_5").decode('UTF-8').split('\n')
                ssh.close()

                flag = {'root': 0, 'vdb': 0, 'vdc': 0}
                for i in output_list:
                    if 'vda1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that bootdisk mounted is shown on FVM instance",
                            tvaultconf.PASS)
                        flag['root'] = 1
                        if 'File_5' in i:
                            reporting.add_test_step(
                                "Verification of bootdisk file's existance on "\
                                        "mounted snapshot", tvaultconf.PASS)
                        else:
                            reporting.add_test_step(
                                "Verification of bootdisk file's existance on "\
                                        "mounted snapshot", tvaultconf.FAIL)
                    if 'vdb1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that volume1 mounted is shown on FVM instance",
                            tvaultconf.PASS)
                        flag['vdb'] = 1
                        if 'File_5' in i:
                            reporting.add_test_step(
                                "Verification of volume1 file's existance on "\
                                        "mounted snapshot", tvaultconf.PASS)
                        else:
                            reporting.add_test_step(
                                "Verification of volume1 file's existance on "\
                                        "mounted snapshot", tvaultconf.FAIL)
                    if 'vdc1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that volume2 mounted is shown on FVM instance",
                            tvaultconf.PASS)
                        flag['vdc'] = 1
                        if 'File_5' in i:
                            reporting.add_test_step(
                                "Verification of volume2 file's existance on "\
                                        "mounted snapshot", tvaultconf.PASS)
                        else:
                            reporting.add_test_step(
                                "Verification of volume2 file's existance on "\
                                        "mounted snapshot", tvaultconf.FAIL)
                for k,v in flag.items():
                    if v == 0:
                        reporting.add_test_step("Verify that mountpoint "\
                                "mounted is shown on FVM instance",
                                tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Snapshot mount of incremental snapshot", tvaultconf.FAIL)

            unmount_status = self.unmount_snapshot(self.wid, self.snapshot_id2)
            LOG.debug("VALUE OF is_unmounted: " + str(unmount_status))
            if unmount_status:
                reporting.add_test_step(
                    "Snapshot unmount of incremental snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1], CONF.validation.fvm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh)
                ssh.close()

                if output_list == b'':
                    reporting.add_test_step(
                        "Unmount incremental snapshot", tvaultconf.PASS)
                    tests[3][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception(
                        "Snapshot unmount of incremental snapshot")
            else:
                raise Exception(
                    "Snapshot unmount of incremental snapshot")

            #File search
            reporting.add_test_script(tests[4][0])
            filecount_in_snapshots = {
                self.snapshot_id: 0,
                self.snapshot_id2: 1}
            filesearch_id = self.filepath_search(
                self.vm_id, "/root/File_5")
            snapshot_wise_filecount = self.verifyFilepath_Search(
                filesearch_id, "/root/File_5")
            for snapshot_id in filecount_in_snapshots.keys():
                if snapshot_wise_filecount[snapshot_id] == filecount_in_snapshots[snapshot_id]:
                    filesearch_status = True
                else:
                    filesearch_status = False

            if filesearch_status:
                LOG.debug("Filepath_Search default_parameters successful")
                reporting.add_test_step(
                    "Verification of Filesearch with default parameters",
                    tvaultconf.PASS)
                tests[4][1] = 1
            else:
                LOG.debug("Filepath Search default_parameters unsuccessful")
                reporting.add_test_step(
                        "Verification of Filesearch with default parameters",
                        tvaultconf.FAIL)
            reporting.test_case_to_write()
            tests[4][1] = 1

            #selective restore
            reporting.add_test_script(tests[5][0])
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
                self.set_floating_ip(fip[2], vm_list[0])
                LOG.debug("Floating ip assigned to selective restored vm -> " +\
                        f"{fip[2]}")
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[2])
                md5sums_after_full_selective = {}
                self.execute_command_disk_mount(ssh, fip[2],
                        tvaultconf.volumes_parts, tvaultconf.mount_points)
                time.sleep(5)
                md5sums_after_full_selective['root'] = self.calculatemmd5checksum(ssh, "/root")
                for mp in tvaultconf.mount_points:
                    md5sums_after_full_selective[mp] = self.calculatemmd5checksum(ssh, mp)
                LOG.debug(f"md5sums_after_full_selective: {md5sums_after_full_selective}")
                ssh.close()

                if md5sums_before_full == \
                        md5sums_after_full_selective:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.PASS)
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Selective restore of full snapshot",
                        tvaultconf.FAIL)

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
                self.set_floating_ip(fip[3], vm_list[0])
                LOG.debug("Floating ip assigned to selective restored vm -> " +\
                        f"{fip[3]}")
                md5sums_after_incr_selective = {}
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[3])
                self.execute_command_disk_mount(ssh, fip[3],
                        tvaultconf.volumes_parts, tvaultconf.mount_points)
                time.sleep(5)
                md5sums_after_incr_selective['root'] = self.calculatemmd5checksum(ssh, "/root")
                for mp in tvaultconf.mount_points:
                    md5sums_after_incr_selective[mp] = self.calculatemmd5checksum(ssh, mp)
                LOG.debug(f"md5sums_after_incr_selective: {md5sums_after_incr_selective}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_selective:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.PASS)
                    tests[5][1] = 1
                    reporting.test_case_to_write()
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Selective restore of incremental snapshot",
                        tvaultconf.FAIL)
            reporting.test_case_to_write()
            tests[5][1] = 1

            #Inplace restore for full snapshot
            reporting.add_test_script(tests[6][0])
            rest_details = {}
            rest_details['rest_type'] = 'inplace'
            rest_details['instances'] = {self.vm_id: self.volumes}
            payload = self.create_restore_json(rest_details)
            # Trigger inplace restore of full snapshot
            restore_id_3 = self.snapshot_inplace_restore(
                self.wid, self.snapshot_id, payload)
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id)
            if(self.getRestoreStatus(self.wid, self.snapshot_id,
                    restore_id_3) == "available"):
                reporting.add_test_step("Inplace restore of full snapshot",
                        tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                self.execute_command_disk_mount(ssh, fip[0],
                        tvaultconf.volumes_parts, tvaultconf.mount_points)
                time.sleep(5)
                md5sums_after_full_inplace = {}
                md5sums_after_full_inplace['root'] = self.calculatemmd5checksum(ssh, "/root")
                for mp in tvaultconf.mount_points:
                    md5sums_after_full_inplace[mp] = self.calculatemmd5checksum(ssh, mp)
                LOG.debug(f"md5sums_after_full_inplace: {md5sums_after_full_inplace}")
                ssh.close()

                if md5sums_before_full == \
                        md5sums_after_full_inplace:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.PASS)
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Inplace restore of full snapshot",
                        tvaultconf.FAIL)

            # Trigger inplace restore of incremental snapshot
            restore_id_4 = self.snapshot_inplace_restore(
                self.wid, self.snapshot_id2, payload)
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id2)
            if(self.getRestoreStatus(self.wid, self.snapshot_id2,
                    restore_id_4) == "available"):
                reporting.add_test_step("Inplace restore of incremental snapshot",
                        tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                self.execute_command_disk_mount(ssh, fip[0],
                        tvaultconf.volumes_parts, tvaultconf.mount_points)
                time.sleep(5)
                md5sums_after_incr_inplace = {}
                md5sums_after_incr_inplace['root'] = self.calculatemmd5checksum(ssh, "/root")
                for mp in tvaultconf.mount_points:
                    md5sums_after_incr_inplace[mp] = self.calculatemmd5checksum(ssh, mp)
                LOG.debug(f"md5sums_after_incr_inplace: {md5sums_after_incr_inplace}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_inplace:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.PASS)
                    tests[6][1] = 1
                    reporting.test_case_to_write()
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Inplace restore of incremental snapshot",
                        tvaultconf.FAIL)
            reporting.test_case_to_write()
            tests[6][1] = 1

            reporting.add_test_script(tests[7][0])
            self.delete_vm(self.vm_id)
            time.sleep(10)
            rest_details = {}
            rest_details['rest_type'] = 'oneclick'
            payload = self.create_restore_json(rest_details)
            # Trigger oneclick restore of full snapshot
            restore_id_5 = self.snapshot_inplace_restore(
                self.wid, self.snapshot_id, payload)
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id)
            if(self.getRestoreStatus(self.wid, self.snapshot_id,
                    restore_id_5) == "available"):
                reporting.add_test_step("Oneclick restore of full snapshot",
                        tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                self.execute_command_disk_mount(ssh, fip[0],
                        tvaultconf.volumes_parts, tvaultconf.mount_points)
                time.sleep(5)
                md5sums_after_full_oneclick = {}
                md5sums_after_full_oneclick['root'] = self.calculatemmd5checksum(ssh, "/root")
                for mp in tvaultconf.mount_points:
                    md5sums_after_full_oneclick[mp] = self.calculatemmd5checksum(ssh, mp)
                LOG.debug(f"md5sums_after_full_oneclick: {md5sums_after_full_oneclick}")
                ssh.close()

                if md5sums_before_full == \
                        md5sums_after_full_oneclick:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.PASS)
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Oneclick restore of full snapshot",
                        tvaultconf.FAIL)

            vm_list = self.get_restored_vm_list(restore_id_5)
            LOG.debug(f"vm_list: {vm_list}, self.vm_id: {self.vm_id}")
            self.delete_vm(vm_list[0])
            time.sleep(5)
            rest_details = {}
            rest_details['rest_type'] = 'oneclick'
            payload = self.create_restore_json(rest_details)
            # Trigger oneclick restore of incremental snapshot
            restore_id_6 = self.snapshot_inplace_restore(
                self.wid, self.snapshot_id2, payload)
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id2)
            if(self.getRestoreStatus(self.wid, self.snapshot_id2,
                    restore_id_6) == "available"):
                reporting.add_test_step("Oneclick restore of incremental snapshot",
                        tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                self.execute_command_disk_mount(ssh, fip[0],
                        tvaultconf.volumes_parts, tvaultconf.mount_points)
                time.sleep(5)
                md5sums_after_incr_oneclick = {}
                md5sums_after_incr_oneclick['root'] = self.calculatemmd5checksum(ssh, "/root")
                for mp in tvaultconf.mount_points:
                    md5sums_after_incr_oneclick[mp] = self.calculatemmd5checksum(ssh, mp)
                LOG.debug(f"md5sums_after_incr_oneclick: {md5sums_after_incr_oneclick}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_oneclick:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.PASS)
                    tests[7][1] = 1
                    reporting.test_case_to_write()
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.FAIL)
            else:
                reporting.add_test_step("Oneclick restore of incremental snapshot",
                        tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            for test in tests:
                if test[1] != 1:
                    reporting.set_test_script_status(tvaultconf.FAIL)
                    reporting.add_test_script(test[0])
                    reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_3_barbican(self):
        try:
            test_var = "tempest.api.workloadmgr.barbican.test_volume_booted_"
            tests = [[test_var+"workload_api", 0],
                    [test_var+"full_snapshot_api", 0],
                    [test_var+"incremental_snapshot_api", 0],
                    [test_var+"snapshot_mount_api", 0],
                    [test_var+"filesearch_api", 0],
                    [test_var+"selectiverestore_api", 0],
                    [test_var+"inplacerestore_api", 0],
                    [test_var+"oneclickrestore_api", 0]]
            reporting.add_test_script(tests[0][0])
            self.kp = self.create_key_pair(tvaultconf.key_pair_name)
            self.volumes = []
            self.boot_volume_id = self.create_volume(
                size=tvaultconf.bootfromvol_vol_size,
                image_id=CONF.compute.image_ref,
                volume_cleanup=False)
            self.set_volume_as_bootable(self.boot_volume_id)
            LOG.debug(f"Bootable Volume ID : {self.boot_volume_id}")
            self.block_mapping_details = [{"source_type": "volume",
                                           "delete_on_termination": "false",
                                           "boot_index": 0,
                                           "uuid": self.boot_volume_id,
                                           "destination_type": "volume"}]
            self.vm_id = self.create_vm(
                key_pair=self.kp,
                image_id="",
                block_mapping_data=self.block_mapping_details,
                vm_cleanup=False)
            fip = self.get_floating_ips()
            LOG.debug("\nAvailable floating ips are {}: \n".format(fip))
            if len(fip) < 4:
                raise Exception("Floating ips unavailable")
            self.set_floating_ip(fip[0], self.vm_id)

            self.frm_id = self.create_vm(
                vm_name="file_recovery_manager",
                flavor_id=CONF.compute.flavor_ref_alt,
                user_data=tvaultconf.user_frm_data,
                key_pair=self.kp,
                image_id=list(CONF.compute.fvm_image_ref.values())[0])
            LOG.debug("FRM Instance ID: " + str(self.frm_id))
            self.set_floating_ip(fip[1], self.frm_id)

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            stdin, stdout, stderr = ssh.exec_command("sudo apt install qemu-guest-agent")
            self.addCustomfilesOnLinuxVM(ssh, "/root", 3)
            md5sums_before_full = self.calculatemmd5checksum(ssh, "/root")
            LOG.debug(f"md5sums_before_full: {md5sums_before_full}")
            ssh.close()
            self.secret_uuid = self.create_secret()

            # Create workload with API
            try:
                self.wid = self.workload_create([self.vm_id],
                        tvaultconf.workload_type_id, encryption=True,
                        secret_uuid=self.secret_uuid)
                LOG.debug("Workload ID: " + str(self.wid))
            except Exception as e:
                LOG.error(f"Exception: {e}")
                raise Exception("Create encrypted workload "\
                        "with volume booted vm")
            if(self.wid is not None):
                self.wait_for_workload_tobe_available(self.wid)
                self.workload_status = self.getWorkloadStatus(self.wid)
                if(self.workload_status == "available"):
                    reporting.add_test_step("Create encrypted workload "\
                            "with volume booted vm", tvaultconf.PASS)
                    tests[0][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Create encrypted workload "\
                         "with volume booted vm")
            else:
                raise Exception("Create encrypted workload with volume "\
                        "booted vm")

            reporting.add_test_script(tests[1][0])
            self.snapshot_id = self.workload_snapshot(self.wid, True)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id)
            if(self.snapshot_status == "available"):
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                self.mount_path = self.get_mountpoint_path(
                        tvaultconf.tvault_ip[0], tvaultconf.tvault_username,
                        tvaultconf.tvault_password)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                        tvaultconf.tvault_ip[0], tvaultconf.tvault_username,
                        tvaultconf.tvault_password, self.mount_path,
                        self.wid, self.snapshot_id)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on "\
                            "target backend", tvaultconf.PASS)
                    tests[1][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create full snapshot")

            reporting.add_test_script(tests[2][0])
            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.addCustomfilesOnLinuxVM(ssh, "/root", 5)
            md5sums_before_incr = self.calculatemmd5checksum(ssh, "/root")
            LOG.debug(f"md5sums_before_incr: {md5sums_before_incr}")
            ssh.close()

            self.snapshot_id2 = self.workload_snapshot(self.wid, False)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id2)
            if(self.snapshot_status == "available"):
                reporting.add_test_step("Create incremental snapshot", tvaultconf.PASS)
                self.mount_path = self.get_mountpoint_path(
                        tvaultconf.tvault_ip[0], tvaultconf.tvault_username,
                        tvaultconf.tvault_password)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                        tvaultconf.tvault_ip[0], tvaultconf.tvault_username,
                        tvaultconf.tvault_password, self.mount_path,
                        self.wid, self.snapshot_id2)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on "\
                            "target backend", tvaultconf.PASS)
                    tests[2][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create incremental snapshot")
                #reporting.add_test_step("Create incremental snapshot", tvaultconf.FAIL)
                #reporting.set_test_script_status(tvaultconf.FAIL)

            reporting.add_test_script(tests[3][0])
            # Mount full snapshot
            mount_status = self.mount_snapshot(
                self.wid, self.snapshot_id, self.frm_id)
            LOG.debug(f"mount_status for full snapshot: {mount_status}")
            if mount_status:
                reporting.add_test_step(
                    "Snapshot mount of full snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1],CONF.validation.fvm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh).decode('UTF-8').split('\n')
                ssh.close()
                flag = 0
                for i in output_list:
                    if 'vda1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that mountpoint mounted is shown on FVM instance",
                            tvaultconf.PASS)
                        flag = 1
                        if 'File_1' in i:
                            reporting.add_test_step(
                                "Verification of file's existance on mounted snapshot",
                                tvaultconf.PASS)
                        else:
                            reporting.add_test_step(
                                "Verification of file's existance on mounted snapshot",
                                tvaultconf.FAIL)
                    else:
                        pass

                if flag == 0:
                    reporting.add_test_step(
                        "Verify that mountpoint mounted is shown on FVM instance",
                        tvaultconf.FAIL)
                else:
                    pass

            unmount_status = self.unmount_snapshot(self.wid, self.snapshot_id)
            LOG.debug("VALUE OF is_unmounted: " + str(unmount_status))
            if unmount_status:
                reporting.add_test_step(
                   "Snapshot unmount of full snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                    fip[1], CONF.validation.fvm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh)
                ssh.close()

                if output_list == b'':
                    reporting.add_test_step(
                        "Unmount full snapshot", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                            "Snapshot unmount of full snapshot", tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Snapshot unmount of full snapshot", tvaultconf.FAIL)

            # Mount incremental snapshot
            mount_status = self.mount_snapshot(
                self.wid, self.snapshot_id2, self.frm_id)
            if mount_status:
                reporting.add_test_step(
                    "Snapshot mount of incremental snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1],CONF.validation.fvm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh,
                        file_name="File_5").decode('UTF-8').split('\n')
                ssh.close()
                flag = 0
                for i in output_list:
                    if 'vda1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that mountpoint mounted is shown on FVM instance",
                            tvaultconf.PASS)
                        flag = 1
                        if 'File_5' in i:
                            reporting.add_test_step(
                                "Verification of file's existance on mounted snapshot",
                                tvaultconf.PASS)
                        else:
                            reporting.add_test_step(
                                "Verification of file's existance on mounted snapshot",
                                tvaultconf.FAIL)
                    else:
                        pass

                if flag == 0:
                    reporting.add_test_step(
                        "Verify that mountpoint mounted is shown on FVM instance",
                        tvaultconf.FAIL)
                else:
                    pass

            unmount_status = self.unmount_snapshot(self.wid, self.snapshot_id2)
            LOG.debug("VALUE OF is_unmounted: " + str(unmount_status))
            if unmount_status:
                reporting.add_test_step(
                    "Snapshot unmount of incremental snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1], CONF.validation.fvm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh)
                ssh.close()

                if output_list == b'':
                    reporting.add_test_step(
                        "Unmount incremental snapshot", tvaultconf.PASS)
                    tests[3][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception(
                        "Snapshot unmount of incremental snapshot")
            else:
                raise Exception(
                    "Snapshot unmount of incremental snapshot")

            #File search
            reporting.add_test_script(tests[4][0])
            filecount_in_snapshots = {
                self.snapshot_id: 0,
                self.snapshot_id2: 1}
            filesearch_id = self.filepath_search(
                self.vm_id, "/root/File_4")
            snapshot_wise_filecount = self.verifyFilepath_Search(
                filesearch_id, "/root/File_4")
            for snapshot_id in filecount_in_snapshots.keys():
                if snapshot_wise_filecount[snapshot_id] == filecount_in_snapshots[snapshot_id]:
                    filesearch_status = True
                else:
                    filesearch_status = False

            if filesearch_status:
                LOG.debug("Filepath_Search default_parameters successful")
                reporting.add_test_step(
                    "Verification of Filesearch with default parameters",
                    tvaultconf.PASS)
                tests[4][1] = 1
            else:
                LOG.debug("Filepath Search default_parameters unsuccessful")
                reporting.add_test_step(
                        "Verification of Filesearch with default parameters",
                        tvaultconf.FAIL)
            reporting.test_case_to_write()
            tests[4][1] = 1

            #selective restore
            reporting.add_test_script(tests[5][0])
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
                self.set_floating_ip(fip[2], vm_list[0])
                LOG.debug("Floating ip assigned to selective restored vm -> " +\
                        f"{fip[2]}")
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[2])
                md5sums_after_full_selective = self.calculatemmd5checksum(ssh, "/root")
                LOG.debug(f"md5sums_after_full_selective: {md5sums_after_full_selective}")
                ssh.close()

                if md5sums_before_full == \
                        md5sums_after_full_selective:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Selective restore of full snapshot",
                        tvaultconf.FAIL)

            # Trigger selective restore of incremental snapshot
            restore_id_2 = self.snapshot_selective_restore(
                self.wid, self.snapshot_id2,
                restore_name="selective_restore_full_snap",
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
                self.set_floating_ip(fip[3], vm_list[0])
                LOG.debug("Floating ip assigned to selective restored vm -> " +\
                        f"{fip[3]}")
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[3])
                md5sums_after_incr_selective = self.calculatemmd5checksum(ssh, "/root")
                LOG.debug(f"md5sums_after_incr_selective: {md5sums_after_incr_selective}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_selective:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
                    tests[5][1] = 1
                    reporting.test_case_to_write()
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Selective restore of incremental snapshot",
                        tvaultconf.FAIL)
            reporting.test_case_to_write()
            tests[5][1] = 1

            #Inplace restore for full snapshot
            reporting.add_test_script(tests[6][0])
            rest_details = {}
            rest_details['rest_type'] = 'inplace'
            rest_details['instances'] = {self.vm_id: self.volumes}
            payload = self.create_restore_json(rest_details)
            # Trigger inplace restore of full snapshot
            restore_id_3 = self.snapshot_inplace_restore(
                self.wid, self.snapshot_id, payload)
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id)
            if(self.getRestoreStatus(self.wid, self.snapshot_id,
                    restore_id_3) == "available"):
                reporting.add_test_step("Inplace restore of full snapshot",
                        tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                md5sums_after_full_inplace = self.calculatemmd5checksum(ssh, "/root")
                LOG.debug(f"md5sums_after_full_inplace: {md5sums_after_full_inplace}")
                ssh.close()

                if md5sums_before_full == \
                        md5sums_after_full_inplace:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Inplace restore of full snapshot",
                        tvaultconf.FAIL)

            # Trigger inplace restore of incremental snapshot
            restore_id_4 = self.snapshot_inplace_restore(
                self.wid, self.snapshot_id2, payload)
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id2)
            if(self.getRestoreStatus(self.wid, self.snapshot_id2,
                    restore_id_4) == "available"):
                reporting.add_test_step("Inplace restore of incremental snapshot",
                        tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                md5sums_after_incr_inplace = self.calculatemmd5checksum(ssh, "/root")
                LOG.debug(f"md5sums_after_incr_inplace: {md5sums_after_incr_inplace}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_inplace:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
                    tests[6][1] = 1
                    reporting.test_case_to_write()
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Inplace restore of incremental snapshot",
                        tvaultconf.FAIL)
            reporting.test_case_to_write()
            tests[6][1] = 1

            reporting.add_test_script(tests[7][0])
            self.delete_vm(self.vm_id)
            time.sleep(10)
            rest_details = {}
            rest_details['rest_type'] = 'oneclick'
            payload = self.create_restore_json(rest_details)
            # Trigger oneclick restore of full snapshot
            restore_id_5 = self.snapshot_inplace_restore(
                self.wid, self.snapshot_id, payload)
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id)
            if(self.getRestoreStatus(self.wid, self.snapshot_id,
                    restore_id_5) == "available"):
                reporting.add_test_step("Oneclick restore of full snapshot",
                        tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                md5sums_after_full_oneclick = self.calculatemmd5checksum(ssh, "/root")
                LOG.debug(f"md5sums_after_full_oneclick: {md5sums_after_full_oneclick}")
                ssh.close()

                if md5sums_before_full == \
                        md5sums_after_full_oneclick:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Oneclick restore of full snapshot",
                        tvaultconf.FAIL)

            vm_list = self.get_restored_vm_list(restore_id_5)
            LOG.debug(f"vm_list: {vm_list}, self.vm_id: {self.vm_id}")
            self.delete_vm(vm_list[0])
            time.sleep(5)
            rest_details = {}
            rest_details['rest_type'] = 'oneclick'
            payload = self.create_restore_json(rest_details)
            # Trigger oneclick restore of incremental snapshot
            restore_id_6 = self.snapshot_inplace_restore(
                self.wid, self.snapshot_id2, payload)
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id2)
            if(self.getRestoreStatus(self.wid, self.snapshot_id2,
                    restore_id_6) == "available"):
                reporting.add_test_step("Oneclick restore of incremental snapshot",
                        tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                md5sums_after_incr_oneclick = self.calculatemmd5checksum(ssh, "/root")
                LOG.debug(f"md5sums_after_incr_oneclick: {md5sums_after_incr_oneclick}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_oneclick:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
                    tests[7][1] = 1
                    reporting.test_case_to_write()
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Oneclick restore of incremental snapshot",
                        tvaultconf.FAIL)

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
    def test_4_barbican(self):
        try:
            test_var = "tempest.api.workloadmgr.barbican.test_volume_boot_vol_attach_"
            tests = [[test_var+"workload_api", 0],
                    [test_var+"full_snapshot_api", 0],
                    [test_var+"incremental_snapshot_api", 0],
                    [test_var+"snapshot_mount_api", 0],
                    [test_var+"filesearch_api", 0],
                    [test_var+"selectiverestore_api", 0],
                    [test_var+"inplacerestore_api", 0],
                    [test_var+"oneclickrestore_api", 0]]
            reporting.add_test_script(tests[0][0])
            self.kp = self.create_key_pair(tvaultconf.key_pair_name)
            self.boot_volume_id = self.create_volume(
                size=tvaultconf.bootfromvol_vol_size,
                image_id=CONF.compute.image_ref,
                volume_cleanup=False)
            self.set_volume_as_bootable(self.boot_volume_id)
            LOG.debug(f"Bootable Volume ID : {self.boot_volume_id}")
            self.block_mapping_details = [{"source_type": "volume",
                                           "delete_on_termination": "false",
                                           "boot_index": 0,
                                           "uuid": self.boot_volume_id,
                                           "destination_type": "volume"}]
            self.vm_id = self.create_vm(
                key_pair=self.kp,
                image_id="",
                block_mapping_data=self.block_mapping_details,
                vm_cleanup=False)
            fip = self.get_floating_ips()
            LOG.debug("\nAvailable floating ips are {}: \n".format(fip))
            if len(fip) < 4:
                raise Exception("Floating ips unavailable")
            self.set_floating_ip(fip[0], self.vm_id)
            self.volumes = []
            for i in range(2):
                self.volume_id = self.create_volume(
                        volume_type_id=CONF.volume.volume_type_id)
                self.volumes.append(self.volume_id)
                self.attach_volume(self.volume_id, self.vm_id)
            LOG.debug(f"Volumes attached: {self.volumes}")

            self.secret_uuid = self.create_secret()
            self.frm_id = self.create_vm(
                vm_name="file_recovery_manager",
                flavor_id=CONF.compute.flavor_ref_alt,
                user_data=tvaultconf.user_frm_data,
                key_pair=self.kp,
                image_id=list(CONF.compute.fvm_image_ref.values())[0])
            LOG.debug("FRM Instance ID: " + str(self.frm_id))
            self.set_floating_ip(fip[1], self.frm_id)

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            stdin, stdout, stderr = ssh.exec_command("sudo apt install qemu-guest-agent")
            self.addCustomfilesOnLinuxVM(ssh, "/root", 3)
            self.execute_command_disk_create(ssh, fip[0],
                    tvaultconf.volumes_parts, tvaultconf.mount_points)
            self.execute_command_disk_mount(ssh, fip[0],
                    tvaultconf.volumes_parts, tvaultconf.mount_points)
            for mp in tvaultconf.mount_points:
                self.addCustomfilesOnLinuxVM(ssh, mp, 4)

            md5sums_before_full = {}
            md5sums_before_full['root'] = self.calculatemmd5checksum(ssh, "/root")
            for mp in tvaultconf.mount_points:
                md5sums_before_full[mp] = self.calculatemmd5checksum(ssh, mp)
            LOG.debug(f"md5sums_before_full: {md5sums_before_full}")
            ssh.close()

            # Create workload with API
            try:
                self.wid = self.workload_create([self.vm_id],
                        tvaultconf.workload_type_id, encryption=True,
                        secret_uuid=self.secret_uuid)
                LOG.debug("Workload ID: " + str(self.wid))
            except Exception as e:
                LOG.error(f"Exception: {e}")
                raise Exception("Create encrypted workload "\
                        "with volume booted vm and vol attached")
            if(self.wid is not None):
                self.wait_for_workload_tobe_available(self.wid)
                self.workload_status = self.getWorkloadStatus(self.wid)
                if(self.workload_status == "available"):
                    reporting.add_test_step("Create encrypted workload "\
                            "with volume booted vm and vol attached",
                            tvaultconf.PASS)
                    tests[0][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Create encrypted workload "\
                         "with image booted vm and vol attached")
            else:
                raise Exception("Create encrypted workload with image "\
                        "booted vm and vol attached")

            reporting.add_test_script(tests[1][0])
            self.snapshot_id = self.workload_snapshot(self.wid, True)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id)
            if(self.snapshot_status == "available"):
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                self.mount_path = self.get_mountpoint_path(
                        tvaultconf.tvault_ip[0], tvaultconf.tvault_username,
                        tvaultconf.tvault_password)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                        tvaultconf.tvault_ip[0], tvaultconf.tvault_username,
                        tvaultconf.tvault_password, self.mount_path,
                        self.wid, self.snapshot_id)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on "\
                            "target backend", tvaultconf.PASS)
                    tests[1][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create full snapshot")

            reporting.add_test_script(tests[2][0])
            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.addCustomfilesOnLinuxVM(ssh, "/root", 6)
            md5sums_before_incr = {}
            md5sums_before_incr['root'] = self.calculatemmd5checksum(ssh, "/root")
            for mp in tvaultconf.mount_points:
                self.addCustomfilesOnLinuxVM(ssh, mp, 6)
                md5sums_before_incr[mp] = self.calculatemmd5checksum(ssh, mp)
            LOG.debug(f"md5sums_before_incr: {md5sums_before_incr}")
            ssh.close()

            self.snapshot_id2 = self.workload_snapshot(self.wid, False)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id2)
            if(self.snapshot_status == "available"):
                reporting.add_test_step("Create incremental snapshot", tvaultconf.PASS)
                self.mount_path = self.get_mountpoint_path(
                        tvaultconf.tvault_ip[0], tvaultconf.tvault_username,
                        tvaultconf.tvault_password)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                        tvaultconf.tvault_ip[0], tvaultconf.tvault_username,
                        tvaultconf.tvault_password, self.mount_path,
                        self.wid, self.snapshot_id2)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on "\
                            "target backend", tvaultconf.PASS)
                    tests[2][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create incremental snapshot")

            reporting.add_test_script(tests[3][0])
            # Mount full snapshot
            mount_status = self.mount_snapshot(
                self.wid, self.snapshot_id, self.frm_id)
            LOG.debug(f"mount_status for full snapshot: {mount_status}")
            if mount_status:
                reporting.add_test_step(
                    "Snapshot mount of full snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1],CONF.validation.fvm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh,
                        file_name="File_2").decode('UTF-8').split('\n')
                ssh.close()
                flag = {'root': 0, 'vdb': 0, 'vdc': 0}
                for i in output_list:
                    if 'vda1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that bootdisk mounted is shown on FVM "\
                                    "instance", tvaultconf.PASS)
                        flag['root'] = 1
                        if 'File_2' in i:
                            reporting.add_test_step(
                                "Verification of bootdisk file's existance "\
                                        "on mounted snapshot", tvaultconf.PASS)
                        else:
                            reporting.add_test_step(
                                "Verification of bootdisk file's existance on"\
                                        " mounted snapshot", tvaultconf.FAIL)
                    if 'vdb1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that volume1 mounted is shown on FVM "\
                                    "instance", tvaultconf.PASS)
                        flag['vdb'] = 1
                        if 'File_2' in i:
                            reporting.add_test_step(
                                "Verification of volume1 file's existance "\
                                        "on mounted snapshot", tvaultconf.PASS)
                        else:
                            reporting.add_test_step(
                                "Verification of volume1 file's existance "\
                                        "on mounted snapshot", tvaultconf.FAIL)
                    if 'vdc1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that volume2 mounted is shown on FVM "\
                                    "instance", tvaultconf.PASS)
                        flag['vdc'] = 1
                        if 'File_2' in i:
                            reporting.add_test_step(
                                "Verification of volume2 file's existance "\
                                        "on mounted snapshot", tvaultconf.PASS)
                        else:
                            reporting.add_test_step(
                                "Verification of volume2 file's existance "\
                                        "on mounted snapshot", tvaultconf.FAIL)
                for k,v in flag.items():
                    if v == 0:
                        reporting.add_test_step("Verify that mountpoint "\
                                "mounted is shown on FVM instance",
                                tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Snapshot mount of full snapshot", tvaultconf.FAIL)

            unmount_status = self.unmount_snapshot(self.wid, self.snapshot_id)
            LOG.debug("VALUE OF is_unmounted: " + str(unmount_status))
            if unmount_status:
                reporting.add_test_step(
                   "Snapshot unmount of full snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                    fip[1], CONF.validation.fvm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh)
                ssh.close()

                if output_list == b'':
                    reporting.add_test_step(
                        "Unmount full snapshot", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                            "Snapshot unmount of full snapshot", tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Snapshot unmount of full snapshot", tvaultconf.FAIL)

            # Mount incremental snapshot
            mount_status = self.mount_snapshot(
                self.wid, self.snapshot_id2, self.frm_id)
            if mount_status:
                reporting.add_test_step(
                    "Snapshot mount of incremental snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1],CONF.validation.fvm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh,
                        file_name="File_5").decode('UTF-8').split('\n')
                ssh.close()

                flag = {'root': 0, 'vdb': 0, 'vdc': 0}
                for i in output_list:
                    if 'vda1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that bootdisk mounted is shown on FVM instance",
                            tvaultconf.PASS)
                        flag['root'] = 1
                        if 'File_5' in i:
                            reporting.add_test_step(
                                "Verification of bootdisk file's existance on "\
                                        "mounted snapshot", tvaultconf.PASS)
                        else:
                            reporting.add_test_step(
                                "Verification of bootdisk file's existance on "\
                                        "mounted snapshot", tvaultconf.FAIL)
                    if 'vdb1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that volume1 mounted is shown on FVM instance",
                            tvaultconf.PASS)
                        flag['vdb'] = 1
                        if 'File_5' in i:
                            reporting.add_test_step(
                                "Verification of volume1 file's existance on "\
                                        "mounted snapshot", tvaultconf.PASS)
                        else:
                            reporting.add_test_step(
                                "Verification of volume1 file's existance on "\
                                        "mounted snapshot", tvaultconf.FAIL)
                    if 'vdc1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that volume2 mounted is shown on FVM instance",
                            tvaultconf.PASS)
                        flag['vdc'] = 1
                        if 'File_5' in i:
                            reporting.add_test_step(
                                "Verification of volume2 file's existance on "\
                                        "mounted snapshot", tvaultconf.PASS)
                        else:
                            reporting.add_test_step(
                                "Verification of volume2 file's existance on "\
                                        "mounted snapshot", tvaultconf.FAIL)
                for k,v in flag.items():
                    if v == 0:
                        reporting.add_test_step("Verify that mountpoint "\
                                "mounted is shown on FVM instance",
                                tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Snapshot mount of incremental snapshot", tvaultconf.FAIL)

            unmount_status = self.unmount_snapshot(self.wid, self.snapshot_id2)
            LOG.debug("VALUE OF is_unmounted: " + str(unmount_status))
            if unmount_status:
                reporting.add_test_step(
                    "Snapshot unmount of incremental snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1], CONF.validation.fvm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh)
                ssh.close()

                if output_list == b'':
                    reporting.add_test_step(
                        "Unmount incremental snapshot", tvaultconf.PASS)
                    tests[3][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception(
                        "Snapshot unmount of incremental snapshot")
            else:
                raise Exception(
                    "Snapshot unmount of incremental snapshot")

            #File search
            reporting.add_test_script(tests[4][0])
            filecount_in_snapshots = {
                self.snapshot_id: 0,
                self.snapshot_id2: 1}
            filesearch_id = self.filepath_search(
                self.vm_id, "/root/File_5")
            snapshot_wise_filecount = self.verifyFilepath_Search(
                filesearch_id, "/root/File_5")
            for snapshot_id in filecount_in_snapshots.keys():
                if snapshot_wise_filecount[snapshot_id] == filecount_in_snapshots[snapshot_id]:
                    filesearch_status = True
                else:
                    filesearch_status = False

            if filesearch_status:
                LOG.debug("Filepath_Search default_parameters successful")
                reporting.add_test_step(
                    "Verification of Filesearch with default parameters",
                    tvaultconf.PASS)
                tests[4][1] = 1
            else:
                LOG.debug("Filepath Search default_parameters unsuccessful")
                reporting.add_test_step(
                        "Verification of Filesearch with default parameters",
                        tvaultconf.FAIL)
            reporting.test_case_to_write()
            tests[4][1] = 1

            #selective restore
            reporting.add_test_script(tests[5][0])
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
                self.set_floating_ip(fip[2], vm_list[0])
                LOG.debug("Floating ip assigned to selective restored vm -> " +\
                        f"{fip[2]}")
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[2])
                md5sums_after_full_selective = {}
                self.execute_command_disk_mount(ssh, fip[2],
                        tvaultconf.volumes_parts, tvaultconf.mount_points)
                time.sleep(5)
                md5sums_after_full_selective['root'] = self.calculatemmd5checksum(ssh, "/root")
                for mp in tvaultconf.mount_points:
                    md5sums_after_full_selective[mp] = self.calculatemmd5checksum(ssh, mp)
                LOG.debug(f"md5sums_after_full_selective: {md5sums_after_full_selective}")
                ssh.close()

                if md5sums_before_full == \
                        md5sums_after_full_selective:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.PASS)
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Selective restore of full snapshot",
                        tvaultconf.FAIL)

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
                self.set_floating_ip(fip[3], vm_list[0])
                LOG.debug("Floating ip assigned to selective restored vm -> " +\
                        f"{fip[3]}")
                md5sums_after_incr_selective = {}
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[3])
                self.execute_command_disk_mount(ssh, fip[3],
                        tvaultconf.volumes_parts, tvaultconf.mount_points)
                time.sleep(5)
                md5sums_after_incr_selective['root'] = self.calculatemmd5checksum(ssh, "/root")
                for mp in tvaultconf.mount_points:
                    md5sums_after_incr_selective[mp] = self.calculatemmd5checksum(ssh, mp)
                LOG.debug(f"md5sums_after_incr_selective: {md5sums_after_incr_selective}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_selective:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.PASS)
                    tests[5][1] = 1
                    reporting.test_case_to_write()
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Selective restore of incremental snapshot",
                        tvaultconf.FAIL)
            reporting.test_case_to_write()
            tests[5][1] = 1

            #Inplace restore for full snapshot
            reporting.add_test_script(tests[6][0])
            rest_details = {}
            rest_details['rest_type'] = 'inplace'
            rest_details['instances'] = {self.vm_id: self.volumes}
            payload = self.create_restore_json(rest_details)
            # Trigger inplace restore of full snapshot
            restore_id_3 = self.snapshot_inplace_restore(
                self.wid, self.snapshot_id, payload)
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id)
            if(self.getRestoreStatus(self.wid, self.snapshot_id,
                    restore_id_3) == "available"):
                reporting.add_test_step("Inplace restore of full snapshot",
                        tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                self.execute_command_disk_mount(ssh, fip[0],
                        tvaultconf.volumes_parts, tvaultconf.mount_points)
                time.sleep(5)
                md5sums_after_full_inplace = {}
                md5sums_after_full_inplace['root'] = self.calculatemmd5checksum(ssh, "/root")
                for mp in tvaultconf.mount_points:
                    md5sums_after_full_inplace[mp] = self.calculatemmd5checksum(ssh, mp)
                LOG.debug(f"md5sums_after_full_inplace: {md5sums_after_full_inplace}")
                ssh.close()

                if md5sums_before_full == \
                        md5sums_after_full_inplace:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.PASS)
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Inplace restore of full snapshot",
                        tvaultconf.FAIL)

            # Trigger inplace restore of incremental snapshot
            restore_id_4 = self.snapshot_inplace_restore(
                self.wid, self.snapshot_id2, payload)
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id2)
            if(self.getRestoreStatus(self.wid, self.snapshot_id2,
                    restore_id_4) == "available"):
                reporting.add_test_step("Inplace restore of incremental snapshot",
                        tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                self.execute_command_disk_mount(ssh, fip[0],
                        tvaultconf.volumes_parts, tvaultconf.mount_points)
                time.sleep(5)
                md5sums_after_incr_inplace = {}
                md5sums_after_incr_inplace['root'] = self.calculatemmd5checksum(ssh, "/root")
                for mp in tvaultconf.mount_points:
                    md5sums_after_incr_inplace[mp] = self.calculatemmd5checksum(ssh, mp)
                LOG.debug(f"md5sums_after_incr_inplace: {md5sums_after_incr_inplace}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_inplace:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.PASS)
                    tests[6][1] = 1
                    reporting.test_case_to_write()
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Inplace restore of incremental snapshot",
                        tvaultconf.FAIL)
            reporting.test_case_to_write()
            tests[6][1] = 1

            reporting.add_test_script(tests[7][0])
            self.delete_vm(self.vm_id)
            time.sleep(10)
            rest_details = {}
            rest_details['rest_type'] = 'oneclick'
            payload = self.create_restore_json(rest_details)
            # Trigger oneclick restore of full snapshot
            restore_id_5 = self.snapshot_inplace_restore(
                self.wid, self.snapshot_id, payload)
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id)
            if(self.getRestoreStatus(self.wid, self.snapshot_id,
                    restore_id_5) == "available"):
                reporting.add_test_step("Oneclick restore of full snapshot",
                        tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                self.execute_command_disk_mount(ssh, fip[0],
                        tvaultconf.volumes_parts, tvaultconf.mount_points)
                time.sleep(5)
                md5sums_after_full_oneclick = {}
                md5sums_after_full_oneclick['root'] = self.calculatemmd5checksum(ssh, "/root")
                for mp in tvaultconf.mount_points:
                    md5sums_after_full_oneclick[mp] = self.calculatemmd5checksum(ssh, mp)
                LOG.debug(f"md5sums_after_full_oneclick: {md5sums_after_full_oneclick}")
                ssh.close()

                if md5sums_before_full == \
                        md5sums_after_full_oneclick:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.PASS)
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Oneclick restore of full snapshot",
                        tvaultconf.FAIL)

            vm_list = self.get_restored_vm_list(restore_id_5)
            LOG.debug(f"vm_list: {vm_list}, self.vm_id: {self.vm_id}")
            self.delete_vm(vm_list[0])
            time.sleep(5)
            rest_details = {}
            rest_details['rest_type'] = 'oneclick'
            payload = self.create_restore_json(rest_details)
            # Trigger oneclick restore of incremental snapshot
            restore_id_6 = self.snapshot_inplace_restore(
                self.wid, self.snapshot_id2, payload)
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id2)
            if(self.getRestoreStatus(self.wid, self.snapshot_id2,
                    restore_id_6) == "available"):
                reporting.add_test_step("Oneclick restore of incremental snapshot",
                        tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                self.execute_command_disk_mount(ssh, fip[0],
                        tvaultconf.volumes_parts, tvaultconf.mount_points)
                time.sleep(5)
                md5sums_after_incr_oneclick = {}
                md5sums_after_incr_oneclick['root'] = self.calculatemmd5checksum(ssh, "/root")
                for mp in tvaultconf.mount_points:
                    md5sums_after_incr_oneclick[mp] = self.calculatemmd5checksum(ssh, mp)
                LOG.debug(f"md5sums_after_incr_oneclick: {md5sums_after_incr_oneclick}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_oneclick:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.PASS)
                    tests[7][1] = 1
                    reporting.test_case_to_write()
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.FAIL)
            else:
                reporting.add_test_step("Oneclick restore of incremental snapshot",
                        tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            for test in tests:
                if test[1] != 1:
                    reporting.set_test_script_status(tvaultconf.FAIL)
                    reporting.add_test_script(test[0])
                    reporting.test_case_to_write()

