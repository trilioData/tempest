from tempest.api.workloadmgr import base
from tempest import config
from tempest.lib import decorators
from tempest import test
import time
import datetime
from oslo_log import log as logging
from tempest import tvaultconf
from tempest import reporting
from tempest import command_argument_string
from tempest.util import cli_parser
from tempest.util import query_data
from oslo_serialization import jsonutils as json

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadsTest(base.BaseWorkloadmgrTest):
    credentials = ['primary']
    workload_id = ""
    vm_id = ""
    volume_id = ""
    policy_id = ""
    secret_uuid = ""
    exception = ""

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

    def _check_encryption_on_backend(self, wid, snapshot_id,
                vm_id, disk_names, mount_path):
        encrypted = False
        for disk_name in disk_names:
            snapshot_encrypted = self.check_snapshot_encryption_on_backend(
                            mount_path, wid, snapshot_id,
                            vm_id, disk_name)
            LOG.debug(f"snapshot_encrypted: {snapshot_encrypted}")
            if snapshot_encrypted:
                encrypted = True
        if encrypted:
            reporting.add_test_step("Verify snapshot encryption on "\
                            "target backend", tvaultconf.PASS)
        else:
            reporting.add_test_step("Verify snapshot encryption on "\
                            "target backend", tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

    def _execute_scheduler_trust_validate_cli(self):
        try:
            cmd = command_argument_string.workload_scheduler_trust_check +\
                    self.wid
            resp = eval(cli_parser.cli_output(cmd))
            reporting.add_test_step("Execute scheduler-trust-validate CLI",
                    tvaultconf.PASS)
            self.wlm_trust = resp['trust']
            self.wlm_trust_valid = resp['is_valid']
            self.wlm_scheduler = resp['scheduler_enabled']
        except Exception as e:
            LOG.error(f"Exception in scheduler-trust-validate CLI: {e}")
            raise Exception("Execute scheduler-trust-validate CLI")

    def _filesearch(self, vm_id, filecount_in_snapshots, search_path):
        filesearch_id = self.filepath_search(vm_id, search_path)
        filesearch_status = self.getSearchStatus(filesearch_id)
        if filesearch_status == 'error':
            reporting.add_test_step("File search failed", tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        else:
            snapshot_wise_filecount = self.verifyFilepath_Search(
                filesearch_id, search_path)

            for snapshot_id in filecount_in_snapshots.keys():
                if snapshot_wise_filecount[snapshot_id] == \
                        filecount_in_snapshots[snapshot_id]:
                    filesearch_status = True
                else:
                    filesearch_status = False
            if filesearch_status:
                LOG.debug("Filepath_Search default_parameters successful")
                reporting.add_test_step(
                    "Verification of Filesearch with default parameters",
                    tvaultconf.PASS)
            else:
                LOG.debug("Filepath Search default_parameters unsuccessful")
                reporting.add_test_step(
                        "Verification of Filesearch with default parameters",
                        tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

    def _get_md5sum(self, ssh, paths):
        md5sums = {}
        for pth in paths:
            if pth != 'volumes':
                md5sums[pth] = self.calculatemmd5checksum(ssh, pth)
            else:
                md5sums[pth] = []
                for mp in tvaultconf.mount_points:
                    md5sums[pth].append(self.calculatemmd5checksum(ssh, mp))
                md5sums[pth].sort()
        LOG.debug(f"_get_md5sum data: {md5sums}")
        return md5sums

    @decorators.attr(type='workloadmgr_api')
    def test_01_barbican(self):
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
            self.disk_names = ["vda"]
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
            self._set_frm_user()
            LOG.debug("FRM Instance ID: " + str(self.frm_id))
            self.set_floating_ip(fip[1], self.frm_id)

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.install_qemu(ssh)
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 3)

            md5sums_before_full = self._get_md5sum(ssh, ["/opt"])
            LOG.debug(f"md5sums_before_full: {md5sums_before_full}")
            ssh.close()
            self.mount_path = self.get_mountpoint_path()
            self.secret_uuid = self.create_secret()

            # Create workload with API
            try:
                self.wid = self.workload_create([self.vm_id],
                        encryption=True,
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
            full_snapshot_sizes = []
            incr_snapshot_sizes = []
            self.snapshot_id = self.workload_snapshot(self.wid, True)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id)
            if(self.snapshot_status == "available"):
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                        self.mount_path, self.wid, self.snapshot_id)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on "\
                            "target backend", tvaultconf.PASS)
                    self._check_encryption_on_backend(self.wid, self.snapshot_id,
                                                      self.vm_id, self.disk_names, self.mount_path)
                    for disk_name in self.disk_names:
                        full_snapshot_size = int(
                            self.check_snapshot_size_on_backend(self.mount_path, self.wid, self.snapshot_id,
                                                                self.vm_id, disk_name))
                        LOG.debug(f"full snapshot_size for {disk_name}: {full_snapshot_size} MB")
                        full_snapshot_sizes.append({disk_name: full_snapshot_size})
                    LOG.debug(f"Full snapshot sizes for all disks: {full_snapshot_sizes}")
                    tests[1][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create full snapshot")

            reporting.add_test_script(tests[2][0])
            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 5)
            md5sums_before_incr = self._get_md5sum(ssh, ["/opt"])
            LOG.debug(f"md5sums_before_incr: {md5sums_before_incr}")
            ssh.close()

            self.snapshot_id2 = self.workload_snapshot(self.wid, False)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id2)
            if(self.snapshot_status == "available"):
                reporting.add_test_step("Create incremental snapshot", tvaultconf.PASS)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                        self.mount_path, self.wid, self.snapshot_id2)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on "\
                            "target backend", tvaultconf.PASS)
                    self._check_encryption_on_backend(self.wid, self.snapshot_id2,
                                                      self.vm_id, self.disk_names, self.mount_path)
                    for disk_name in self.disk_names:
                        incr_snapshot_size = int(
                            self.check_snapshot_size_on_backend(self.mount_path, self.wid, self.snapshot_id2,
                                                                self.vm_id, disk_name))
                        LOG.debug(f"incr snapshot_size for {disk_name}: {incr_snapshot_size} MB")
                        incr_snapshot_sizes.append({disk_name: incr_snapshot_size})
                    LOG.debug(f"Incr snapshot sizes for all disks: {incr_snapshot_sizes}")
                    for dict1, dict2 in zip(full_snapshot_sizes, incr_snapshot_sizes):
                        for key, value in dict1.items():
                            LOG.debug(f"All values: {dict1} {dict2} {value} {dict2[key]}")
                            if value > dict2[key]:
                                reporting.add_test_step(
                                    f"Full snapshot size is greater than incr snapshot size for {key}", tvaultconf.PASS)
                            else:
                                reporting.add_test_step(
                                    f"Full snapshot size is greater than incr snapshot size for {key}", tvaultconf.FAIL)
                    tests[2][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create incremental snapshot")

            reporting.add_test_script(tests[3][0])
            # Mount full snapshot
            mount_status = self.mount_snapshot(
                self.wid, self.snapshot_id, self.frm_id, mount_cleanup=True)
            LOG.debug(f"mount_status for full snapshot: {mount_status}")
            if mount_status:
                reporting.add_test_step(
                    "Snapshot mount of full snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1],self.frm_ssh_user)
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
            else:
                reporting.add_test_step("Snapshot mount of full snapshot", tvaultconf.FAIL)

            unmount_status = self.unmount_snapshot(self.wid, self.snapshot_id)
            LOG.debug("VALUE OF is_unmounted: " + str(unmount_status))
            if unmount_status:
                reporting.add_test_step(
                   "Snapshot unmount of full snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                    fip[1], self.frm_ssh_user)
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
                self.wid, self.snapshot_id2, self.frm_id, mount_cleanup=True)
            if mount_status:
                reporting.add_test_step(
                    "Snapshot mount of incremental snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1], self.frm_ssh_user)
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
            else:
                reporting.add_test_step(
                    "Snapshot mount of incremental snapshot", tvaultconf.FAIL)

            unmount_status = self.unmount_snapshot(self.wid, self.snapshot_id2)
            LOG.debug("VALUE OF is_unmounted: " + str(unmount_status))
            if unmount_status:
                reporting.add_test_step(
                    "Snapshot unmount of incremental snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1], self.frm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh)
                ssh.close()

                if output_list == b'':
                    reporting.add_test_step(
                        "Unmount incremental snapshot", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Snapshot unmount of incremental snapshot", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Snapshot unmount of incremental snapshot", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
            tests[3][1] = 1

            #File search
            reporting.add_test_script(tests[4][0])
            filecount_in_snapshots = {
                self.snapshot_id: 0,
                self.snapshot_id2: 1}
            search_path = "/opt/File_4"
            self._filesearch(self.vm_id, filecount_in_snapshots, search_path)
            reporting.test_case_to_write()
            tests[4][1] = 1

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 6)
            md5sums_after_incr = self._get_md5sum(ssh, ["/opt"])
            LOG.debug(f"md5sums_after_incr: {md5sums_after_incr}")
            ssh.close()

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
                md5sums_after_full_selective = self._get_md5sum(ssh, ["/opt"])
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
                md5sums_after_incr_selective = self._get_md5sum(ssh, ["/opt"])
                LOG.debug(f"md5sums_after_incr_selective: {md5sums_after_incr_selective}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_selective:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
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
                md5sums_after_full_inplace = self._get_md5sum(ssh, ["/opt"])
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
                md5sums_after_incr_inplace = self._get_md5sum(ssh, ["/opt"])
                LOG.debug(f"md5sums_after_incr_inplace: {md5sums_after_incr_inplace}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_inplace:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
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
                md5sums_after_full_oneclick = self._get_md5sum(ssh, ["/opt"])
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
                md5sums_after_incr_oneclick = self._get_md5sum(ssh, ["/opt"])
                LOG.debug(f"md5sums_after_incr_oneclick: {md5sums_after_incr_oneclick}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_oneclick:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
                    tests[7][1] = 1
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Oneclick restore of incremental snapshot",
                        tvaultconf.FAIL)
            reporting.test_case_to_write()

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
    def test_02_barbican(self):
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
            self.disk_names = ["vda", "vdb", "vdc"]
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
            self._set_frm_user()
            LOG.debug("FRM Instance ID: " + str(self.frm_id))
            self.set_floating_ip(fip[1], self.frm_id)

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.install_qemu(ssh)
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 3)
            self.execute_command_disk_create(ssh, fip[0],
                    tvaultconf.volumes_parts, tvaultconf.mount_points)
            self.execute_command_disk_mount(ssh, fip[0],
                    tvaultconf.volumes_parts, tvaultconf.mount_points)
            for mp in tvaultconf.mount_points:
                self.addCustomfilesOnLinuxVM(ssh, mp, 4)

            md5sums_before_full = self._get_md5sum(ssh, ["/opt", "volumes"])
            LOG.debug(f"md5sums_before_full: {md5sums_before_full}")
            ssh.close()
            self.mount_path = self.get_mountpoint_path()

            # Create workload with API
            try:
                self.wid = self.workload_create([self.vm_id],
                        encryption=True,
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
            full_snapshot_sizes = []
            incr_snapshot_sizes = []
            self.snapshot_id = self.workload_snapshot(self.wid, True)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id)
            if(self.snapshot_status == "available"):
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                        self.mount_path, self.wid, self.snapshot_id)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on "\
                            "target backend", tvaultconf.PASS)
                    self._check_encryption_on_backend(self.wid, self.snapshot_id,
                                                      self.vm_id, self.disk_names, self.mount_path)
                    for disk_name in self.disk_names:
                        full_snapshot_size = int(
                            self.check_snapshot_size_on_backend(self.mount_path, self.wid, self.snapshot_id,
                                                                self.vm_id, disk_name))
                        LOG.debug(f"full snapshot_size for {disk_name}: {full_snapshot_size} MB")
                        full_snapshot_sizes.append({disk_name: full_snapshot_size})
                    LOG.debug(f"Full snapshot sizes for all disks: {full_snapshot_sizes}")
                    tests[1][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create full snapshot")

            reporting.add_test_script(tests[2][0])
            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 6)
            md5sums_before_incr = self._get_md5sum(ssh, ["/opt", "volumes"])
            ssh.close()

            self.snapshot_id2 = self.workload_snapshot(self.wid, False)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id2)
            if(self.snapshot_status == "available"):
                reporting.add_test_step("Create incremental snapshot", tvaultconf.PASS)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                        self.mount_path, self.wid, self.snapshot_id2)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on "\
                            "target backend", tvaultconf.PASS)
                    self._check_encryption_on_backend(self.wid, self.snapshot_id2,
                                                      self.vm_id, self.disk_names, self.mount_path)
                    for disk_name in self.disk_names:
                        incr_snapshot_size = int(
                            self.check_snapshot_size_on_backend(self.mount_path, self.wid, self.snapshot_id2,
                                                                self.vm_id, disk_name))
                        LOG.debug(f"incr snapshot_size for {disk_name}: {incr_snapshot_size} MB")
                        incr_snapshot_sizes.append({disk_name: incr_snapshot_size})
                    LOG.debug(f"Incr snapshot sizes for all disks: {incr_snapshot_sizes}")
                    for dict1, dict2 in zip(full_snapshot_sizes, incr_snapshot_sizes):
                        for key, value in dict1.items():
                            LOG.debug(f"All values: {dict1} {dict2} {value} {dict2[key]}")
                            if value > dict2[key]:
                                reporting.add_test_step(
                                    f"Full snapshot size is greater than incr snapshot size for {key}", tvaultconf.PASS)
                            else:
                                reporting.add_test_step(
                                    f"Full snapshot size is greater than incr snapshot size for {key}", tvaultconf.FAIL)
                    tests[2][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create incremental snapshot")

            reporting.add_test_script(tests[3][0])
            # Mount full snapshot
            mount_status = self.mount_snapshot(
                self.wid, self.snapshot_id, self.frm_id, mount_cleanup=True)
            LOG.debug(f"mount_status for full snapshot: {mount_status}")
            if mount_status:
                reporting.add_test_step(
                    "Snapshot mount of full snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1], self.frm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh,
                        file_name="File_2").decode('UTF-8').split('\n')
                ssh.close()
                flag = {'opt': 0, 'vdb': 0, 'vdc': 0}
                for i in output_list:
                    if 'vda1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that bootdisk mounted is shown on FVM "\
                                    "instance", tvaultconf.PASS)
                        flag['opt'] = 1
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
                LOG.debug(f"Flag: {flag}")
                for k,v in flag.items():
                    LOG.debug(f"k: {k}")
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
                    fip[1], self.frm_ssh_user)
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
                self.wid, self.snapshot_id2, self.frm_id, mount_cleanup=True)
            if mount_status:
                reporting.add_test_step(
                    "Snapshot mount of incremental snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1], self.frm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh,
                        file_name="File_5").decode('UTF-8').split('\n')
                ssh.close()

                flag = {'opt': 0, 'vdb': 0, 'vdc': 0}
                for i in output_list:
                    if 'vda1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that bootdisk mounted is shown on FVM instance",
                            tvaultconf.PASS)
                        flag['opt'] = 1
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
                LOG.debug(f"flag: {flag}")
                for k,v in flag.items():
                    LOG.debug(f"k: {k}")
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
                        fip[1], self.frm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh)
                ssh.close()

                if output_list == b'':
                    reporting.add_test_step(
                        "Unmount incremental snapshot", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Snapshot unmount of incremental snapshot", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Snapshot unmount of incremental snapshot", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
            tests[3][1] = 1

            #File search
            reporting.add_test_script(tests[4][0])
            filecount_in_snapshots = {
                self.snapshot_id: 0,
                self.snapshot_id2: 1}
            search_path = "/opt/File_5"
            self._filesearch(self.vm_id, filecount_in_snapshots, search_path)
            reporting.test_case_to_write()
            tests[4][1] = 1

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 7)
            md5sums_after_incr = self._get_md5sum(ssh, ["/opt", "volumes"])
            LOG.debug(f"md5sums_after_incr: {md5sums_after_incr}")
            ssh.close()

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
                self.execute_command_disk_mount(ssh, fip[2],
                        tvaultconf.volumes_parts, tvaultconf.mount_points)
                time.sleep(5)
                md5sums_after_full_selective = self._get_md5sum(ssh, ["/opt", "volumes"])
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
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[3])
                self.execute_command_disk_mount(ssh, fip[3],
                        tvaultconf.volumes_parts, tvaultconf.mount_points)
                time.sleep(5)
                md5sums_after_incr_selective = self._get_md5sum(ssh, ["/opt", "volumes"])
                LOG.debug(f"md5sums_after_incr_selective: {md5sums_after_incr_selective}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_selective:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.PASS)
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
            self.wait_for_workload_tobe_available(self.wid)
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
                md5sums_after_full_inplace = self._get_md5sum(ssh, ["/opt", "volumes"])
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
                md5sums_after_incr_inplace = self._get_md5sum(ssh, ["/opt", "volumes"])
                LOG.debug(f"md5sums_after_incr_inplace: {md5sums_after_incr_inplace}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_inplace:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.PASS)
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
                md5sums_after_full_oneclick = self._get_md5sum(ssh, ["/opt", "volumes"])
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
                md5sums_after_incr_oneclick = self._get_md5sum(ssh, ["/opt", "volumes"])
                LOG.debug(f"md5sums_after_incr_oneclick: {md5sums_after_incr_oneclick}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_oneclick:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.PASS)
                    tests[7][1] = 1
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.FAIL)
            else:
                reporting.add_test_step("Oneclick restore of incremental snapshot",
                        tvaultconf.FAIL)
            reporting.test_case_to_write()

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
    def test_03_barbican(self):
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
            self.disk_names = ["vda"]
            self.boot_volume_id = self.create_volume(
                size=tvaultconf.bootfromvol_vol_size,
                image_id=CONF.compute.image_ref,
                volume_cleanup=True)
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
                vm_cleanup=True)
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
            self._set_frm_user()
            LOG.debug("FRM Instance ID: " + str(self.frm_id))
            self.set_floating_ip(fip[1], self.frm_id)

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.install_qemu(ssh)
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 3)
            md5sums_before_full = self._get_md5sum(ssh, ["/opt"])
            LOG.debug(f"md5sums_before_full: {md5sums_before_full}")
            ssh.close()
            self.mount_path = self.get_mountpoint_path()
            self.secret_uuid = self.create_secret()

            # Create workload with API
            try:
                self.wid = self.workload_create([self.vm_id],
                        encryption=True,
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
            full_snapshot_sizes = []
            incr_snapshot_sizes = []
            self.snapshot_id = self.workload_snapshot(self.wid, True)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id)
            if(self.snapshot_status == "available"):
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                        self.mount_path, self.wid, self.snapshot_id)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on "\
                            "target backend", tvaultconf.PASS)
                    self._check_encryption_on_backend(self.wid, self.snapshot_id,
                                                      self.vm_id, self.disk_names, self.mount_path)
                    for disk_name in self.disk_names:
                        full_snapshot_size = int(
                            self.check_snapshot_size_on_backend(self.mount_path, self.wid, self.snapshot_id,
                                                                self.vm_id, disk_name))
                        LOG.debug(f"full snapshot_size for {disk_name}: {full_snapshot_size} MB")
                        full_snapshot_sizes.append({disk_name: full_snapshot_size})
                    LOG.debug(f"Full snapshot sizes for all disks: {full_snapshot_sizes}")
                    tests[1][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create full snapshot")

            reporting.add_test_script(tests[2][0])
            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 5)
            md5sums_before_incr = self._get_md5sum(ssh, ["/opt"])
            LOG.debug(f"md5sums_before_incr: {md5sums_before_incr}")
            ssh.close()

            self.snapshot_id2 = self.workload_snapshot(self.wid, False)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id2)
            if(self.snapshot_status == "available"):
                reporting.add_test_step("Create incremental snapshot", tvaultconf.PASS)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                        self.mount_path, self.wid, self.snapshot_id2)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on "\
                            "target backend", tvaultconf.PASS)
                    self._check_encryption_on_backend(self.wid, self.snapshot_id2,
                                                      self.vm_id, self.disk_names, self.mount_path)
                    for disk_name in self.disk_names:
                        incr_snapshot_size = int(
                            self.check_snapshot_size_on_backend(self.mount_path, self.wid, self.snapshot_id2,
                                                                self.vm_id, disk_name))
                        LOG.debug(f"incr snapshot_size for {disk_name}: {incr_snapshot_size} MB")
                        incr_snapshot_sizes.append({disk_name: incr_snapshot_size})
                    LOG.debug(f"Incr snapshot sizes for all disks: {incr_snapshot_sizes}")
                    for dict1, dict2 in zip(full_snapshot_sizes, incr_snapshot_sizes):
                        for key, value in dict1.items():
                            LOG.debug(f"All values: {dict1} {dict2} {value} {dict2[key]}")
                            if value > dict2[key]:
                                reporting.add_test_step(
                                    f"Full snapshot size is greater than incr snapshot size for {key}", tvaultconf.PASS)
                            else:
                                reporting.add_test_step(
                                    f"Full snapshot size is greater than incr snapshot size for {key}", tvaultconf.FAIL)
                    tests[2][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create incremental snapshot")

            reporting.add_test_script(tests[3][0])
            # Mount full snapshot
            mount_status = self.mount_snapshot(
                self.wid, self.snapshot_id, self.frm_id, mount_cleanup=True)
            LOG.debug(f"mount_status for full snapshot: {mount_status}")
            if mount_status:
                reporting.add_test_step(
                    "Snapshot mount of full snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1], self.frm_ssh_user)
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
            else:
                reporting.add_test_step(
                    "Snapshot mount of full snapshot", tvaultconf.FAIL)

            unmount_status = self.unmount_snapshot(self.wid, self.snapshot_id)
            LOG.debug("VALUE OF is_unmounted: " + str(unmount_status))
            if unmount_status:
                reporting.add_test_step(
                   "Snapshot unmount of full snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                    fip[1], self.frm_ssh_user)
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
                self.wid, self.snapshot_id2, self.frm_id, mount_cleanup=True)
            if mount_status:
                reporting.add_test_step(
                    "Snapshot mount of incremental snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1], self.frm_ssh_user)
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
            else:
                reporting.add_test_step(
                    "Snapshot mount of incremental snapshot", tvaultconf.FAIL)
            unmount_status = self.unmount_snapshot(self.wid, self.snapshot_id2)
            LOG.debug("VALUE OF is_unmounted: " + str(unmount_status))
            if unmount_status:
                reporting.add_test_step(
                    "Snapshot unmount of incremental snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1], self.frm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh)
                ssh.close()

                if output_list == b'':
                    reporting.add_test_step(
                        "Unmount incremental snapshot", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Snapshot unmount of incremental snapshot", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Snapshot unmount of incremental snapshot", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
            tests[3][1] = 1

            #File search
            reporting.add_test_script(tests[4][0])
            filecount_in_snapshots = {
                self.snapshot_id: 0,
                self.snapshot_id2: 1}
            search_path = "/opt/File_4"
            self._filesearch(self.vm_id, filecount_in_snapshots, search_path)
            reporting.test_case_to_write()
            tests[4][1] = 1

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 6)
            md5sums_after_incr = self._get_md5sum(ssh, ["/opt"])
            LOG.debug(f"md5sums_after_incr: {md5sums_after_incr}")
            ssh.close()

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
                md5sums_after_full_selective = self._get_md5sum(ssh, ["/opt"])
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
                md5sums_after_incr_selective = self._get_md5sum(ssh, ["/opt"])
                LOG.debug(f"md5sums_after_incr_selective: {md5sums_after_incr_selective}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_selective:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
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
            self.volumes.append(self.boot_volume_id)
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
                md5sums_after_full_inplace = self._get_md5sum(ssh, ["/opt"])
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
                md5sums_after_incr_inplace = self._get_md5sum(ssh, ["/opt"])
                LOG.debug(f"md5sums_after_incr_inplace: {md5sums_after_incr_inplace}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_inplace:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
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
            self.delete_volume(self.boot_volume_id)
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
                md5sums_after_full_oneclick = self._get_md5sum(ssh, ["/opt"])
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
                md5sums_after_incr_oneclick = self._get_md5sum(ssh, ["/opt"])
                LOG.debug(f"md5sums_after_incr_oneclick: {md5sums_after_incr_oneclick}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_oneclick:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
                    tests[7][1] = 1
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Oneclick restore of incremental snapshot",
                        tvaultconf.FAIL)
            reporting.test_case_to_write()

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
    def test_04_barbican(self):
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
                volume_cleanup=True)
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
                vm_cleanup=True)
            fip = self.get_floating_ips()
            LOG.debug("\nAvailable floating ips are {}: \n".format(fip))
            if len(fip) < 4:
                raise Exception("Floating ips unavailable")
            self.set_floating_ip(fip[0], self.vm_id)
            self.volumes = []
            self.disk_names = ["vda", "vdb", "vdc"]
            self.volumes.append(self.boot_volume_id)
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
            self._set_frm_user()
            LOG.debug("FRM Instance ID: " + str(self.frm_id))
            self.set_floating_ip(fip[1], self.frm_id)

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.install_qemu(ssh)
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 3)
            self.execute_command_disk_create(ssh, fip[0],
                    tvaultconf.volumes_parts, tvaultconf.mount_points)
            self.execute_command_disk_mount(ssh, fip[0],
                    tvaultconf.volumes_parts, tvaultconf.mount_points)
            for mp in tvaultconf.mount_points:
                self.addCustomfilesOnLinuxVM(ssh, mp, 4)

            md5sums_before_full = self._get_md5sum(ssh, ["/opt", "volumes"])
            LOG.debug(f"md5sums_before_full: {md5sums_before_full}")
            ssh.close()
            self.mount_path = self.get_mountpoint_path()

            # Create workload with API
            try:
                self.wid = self.workload_create([self.vm_id],
                        encryption=True,
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
            full_snapshot_sizes = 0
            incr_snapshot_sizes = 0
            self.snapshot_id = self.workload_snapshot(self.wid, True)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id)
            if(self.snapshot_status == "available"):
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                        self.mount_path, self.wid, self.snapshot_id)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on "\
                            "target backend", tvaultconf.PASS)
                    self._check_encryption_on_backend(self.wid, self.snapshot_id,
                                                      self.vm_id, self.disk_names, self.mount_path)
                    for disk_name in self.disk_names:
                        full_snapshot_size = int(
                            self.check_snapshot_size_on_backend(self.mount_path, self.wid, self.snapshot_id,
                                                                self.vm_id, disk_name))
                        LOG.debug(f"full snapshot_size for {disk_name}: {full_snapshot_size} MB")
                        full_snapshot_sizes = full_snapshot_sizes + full_snapshot_size
                    LOG.debug(f"Full snapshot sizes for all disks: {full_snapshot_sizes}")
                    tests[1][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create full snapshot")

            reporting.add_test_script(tests[2][0])
            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 6)
            for mp in tvaultconf.mount_points:
                self.addCustomfilesOnLinuxVM(ssh, mp, 6)
            md5sums_before_incr = self._get_md5sum(ssh, ["/opt", "volumes"])
            LOG.debug(f"md5sums_before_incr: {md5sums_before_incr}")
            ssh.close()

            self.snapshot_id2 = self.workload_snapshot(self.wid, False)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id2)
            if(self.snapshot_status == "available"):
                reporting.add_test_step("Create incremental snapshot", tvaultconf.PASS)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                        self.mount_path, self.wid, self.snapshot_id2)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on "\
                            "target backend", tvaultconf.PASS)
                    self._check_encryption_on_backend(self.wid, self.snapshot_id2,
                                                      self.vm_id, self.disk_names, self.mount_path)
                    for disk_name in self.disk_names:
                        incr_snapshot_size = int(
                            self.check_snapshot_size_on_backend(self.mount_path, self.wid, self.snapshot_id2,
                                                                self.vm_id, disk_name))
                        LOG.debug(f"incr snapshot_size for {disk_name}: {incr_snapshot_size} MB")
                        incr_snapshot_sizes = incr_snapshot_sizes + incr_snapshot_size
                    LOG.debug(f"Incr snapshot sizes for all disks: {incr_snapshot_sizes}")
                    if (full_snapshot_sizes > incr_snapshot_sizes):
                        reporting.add_test_step(f"Full snapshot size is greater than incr snapshot size",
                                                tvaultconf.PASS)
                    else:
                        reporting.add_test_step(f"Full snapshot size is greater than incr snapshot size",
                                                tvaultconf.FAIL)
                    tests[2][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create incremental snapshot")

            reporting.add_test_script(tests[3][0])
            # Mount full snapshot
            mount_status = self.mount_snapshot(
                self.wid, self.snapshot_id, self.frm_id, mount_cleanup=True)
            LOG.debug(f"mount_status for full snapshot: {mount_status}")
            if mount_status:
                reporting.add_test_step(
                    "Snapshot mount of full snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1], self.frm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh,
                        file_name="File_2").decode('UTF-8').split('\n')
                ssh.close()
                flag = {'opt': 0, 'vdb': 0, 'vdc': 0}
                for i in output_list:
                    if 'vda1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that bootdisk mounted is shown on FVM "\
                                    "instance", tvaultconf.PASS)
                        flag['opt'] = 1
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
                    fip[1], self.frm_ssh_user)
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
                self.wid, self.snapshot_id2, self.frm_id, mount_cleanup=True)
            if mount_status:
                reporting.add_test_step(
                    "Snapshot mount of incremental snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1], self.frm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh,
                        file_name="File_5").decode('UTF-8').split('\n')
                ssh.close()

                flag = {'opt': 0, 'vdb': 0, 'vdc': 0}
                for i in output_list:
                    if 'vda1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that bootdisk mounted is shown on FVM instance",
                            tvaultconf.PASS)
                        flag['opt'] = 1
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
                        fip[1], self.frm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh)
                ssh.close()

                if output_list == b'':
                    reporting.add_test_step(
                        "Unmount incremental snapshot", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Snapshot unmount of incremental snapshot", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Snapshot unmount of incremental snapshot", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
            tests[3][1] = 1

            #File search
            reporting.add_test_script(tests[4][0])
            filecount_in_snapshots = {
                    self.snapshot_id: 0,
                    self.snapshot_id2: 1}
            search_path = "/opt/File_5"
            self._filesearch(self.vm_id, filecount_in_snapshots, search_path)
            reporting.test_case_to_write()
            tests[4][1] = 1

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 7)
            for mp in tvaultconf.mount_points:
                self.addCustomfilesOnLinuxVM(ssh, mp, 7)
            md5sums_after_incr = self._get_md5sum(ssh, ["/opt", "volumes"])
            LOG.debug(f"md5sums_after_incr: {md5sums_after_incr}")
            ssh.close()

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
                self.execute_command_disk_mount(ssh, fip[2],
                        tvaultconf.volumes_parts, tvaultconf.mount_points)
                time.sleep(5)
                md5sums_after_full_selective = self._get_md5sum(ssh, ["/opt", "volumes"])
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
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[3])
                self.execute_command_disk_mount(ssh, fip[3],
                        tvaultconf.volumes_parts, tvaultconf.mount_points)
                time.sleep(5)
                md5sums_after_incr_selective = self._get_md5sum(ssh, ["/opt", "volumes"])
                LOG.debug(f"md5sums_after_incr_selective: {md5sums_after_incr_selective}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_selective:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.PASS)
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
                md5sums_after_full_inplace = self._get_md5sum(ssh, ["/opt", "volumes"])
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
                md5sums_after_incr_inplace = self._get_md5sum(ssh, ["/opt", "volumes"])
                LOG.debug(f"md5sums_after_incr_inplace: {md5sums_after_incr_inplace}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_inplace:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.PASS)
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
                md5sums_after_full_oneclick = self._get_md5sum(ssh, ["/opt", "volumes"])
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
                md5sums_after_incr_oneclick = self._get_md5sum(ssh, ["/opt", "volumes"])
                LOG.debug(f"md5sums_after_incr_oneclick: {md5sums_after_incr_oneclick}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_oneclick:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.PASS)
                    tests[7][1] = 1
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification", tvaultconf.FAIL)
            else:
                reporting.add_test_step("Oneclick restore of incremental snapshot",
                        tvaultconf.FAIL)
            reporting.test_case_to_write()

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
    def test_05_barbican(self):
        try:
            reporting.add_test_script(str(__name__) + "_retention")
            vm_id = self.create_vm(vm_cleanup=True)
            LOG.debug("VM ID : " + str(vm_id))
            i = 1
            self.snapshots = []

            jobschedule = {
                'retention_policy_type': 'Number of Snapshots to Keep',
                'retention_policy_value': '3',
                'full_backup_interval': '2'}
            rpv = int(jobschedule['retention_policy_value'])
            self.secret_uuid = self.create_secret()
            workload_id = self.workload_create(
                [vm_id],
                jobschedule=jobschedule,
                encryption=True,
                secret_uuid=self.secret_uuid,
                workload_cleanup=True)
            LOG.debug("Workload ID: " + str(workload_id))
            if(workload_id is not None):
                self.wait_for_workload_tobe_available(workload_id)
                if(self.getWorkloadStatus(workload_id) == "available"):
                    reporting.add_test_step("Create encrypted workload",
                            tvaultconf.PASS)
                else:
                    reporting.add_test_step("Create encrypted workload",
                            tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Create encrypted workload",
                        tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("Encrypted Workload creation failed")

            for i in range(0, (rpv + 1)):
                snapshot_id = self.workload_snapshot(
                    workload_id, True, snapshot_cleanup=True)
                self.snapshots.append(snapshot_id)
                self.wait_for_workload_tobe_available(workload_id)
                if(self.getSnapshotStatus(workload_id, snapshot_id) == "available"):
                    reporting.add_test_step(
                        "Create full snapshot-{}".format(i + 1), tvaultconf.PASS)
                    LOG.debug("Full snapshot available!!")
                else:
                    reporting.add_test_step(
                        "Create full snapshot-{}".format(i + 1), tvaultconf.FAIL)
                    raise Exception("Snapshot creation failed")

            snapshotlist = self.getSnapshotList(workload_id=workload_id)
            LOG.debug(f"Snapshots created in test: {self.snapshots}, "\
                    f"Snapshots returned in snapshot_list: {snapshotlist}")
            if len(snapshotlist) == rpv:
                reporting.add_test_step("Retention", tvaultconf.PASS)
                LOG.debug("Retention worked!!")
            else:
                reporting.add_test_step("Retention", tvaultconf.FAIL)
                LOG.debug("Retention didn't work!!")
                raise Exception("Retention failed")
            if (tvaultconf.cleanup):
                for snapshot in snapshotlist:
                    self.addCleanup(self.snapshot_delete,
                                    workload_id, snapshot)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @test.pre_req({'type': 'barbican_workload'})
    @decorators.attr(type='workloadmgr_cli')
    def test_06_barbican(self):
        try:
            global vm_id
            global secret_uuid
            global volume_id
            test_var = "tempest.api.workloadmgr.barbican.test_"
            tests = [[test_var + "create_workload_with_encryption_CLI", 0],
                     [test_var + "Create_Multiple_workloads_with_same_Secret_UUID", 0],
                     [test_var + "create_workload_with_wrong_secretUUID", 0]]
            reporting.add_test_script(tests[0][0])
            if self.exception != "":
                LOG.debug("pre req failed")
                reporting.add_test_step(str(self.exception), tvaultconf.FAIL)
                raise Exception(str(self.exception))
            LOG.debug("pre req completed")
            vm_id = self.vm_id
            secret_uuid = self.secret_uuid
            volume_id = self.volume_id

            # Create workload with CLI
            workload_create_with_encryption = command_argument_string.workload_create_with_encryption + \
                                              " instance-id=" + str(self.vm_id) + \
                                              " --secret-uuid " + str(self.secret_uuid)
            LOG.debug("WORKLOAD CMD - " + str(workload_create_with_encryption))
            error = cli_parser.cli_error(workload_create_with_encryption)
            if error and (str(error.strip('\n')).find('ERROR') != -1):
                LOG.debug("workload with encryption creation unsuccessful : " + error)
                reporting.add_test_step(
                    "Execute workload_create_with_encryption command",
                    tvaultconf.FAIL)
                raise Exception(
                    "Workload with encryption creation Failed")
            else:
                LOG.debug("workload with encryption created successfully")
                reporting.add_test_step(
                    "Execute workload_create_with_encryption command",
                    tvaultconf.PASS)
                time.sleep(10)
                self.wid1 = query_data.get_workload_id_in_creation(
                    tvaultconf.workload_name)
                workload_available = self.wait_for_workload_tobe_available(
                    self.wid1)
                LOG.debug("Workload ID: " + str(self.wid1))

                # Show workload details using CLI command
                rc = cli_parser.cli_returncode(
                command_argument_string.workload_show + self.wid1)
                if rc != 0:
                    reporting.add_test_step("Execute workload-show command", tvaultconf.FAIL)
                    # raise Exception("Command did not execute correctly : " + str(rc))
                    LOG.debug("Command not executed correctly : " + str(rc))
                else:
                    reporting.add_test_step("Execute workload-show command", tvaultconf.PASS)
                    LOG.debug("Command executed correctly : " + str(rc))

                out = cli_parser.cli_output(
                    command_argument_string.workload_show + self.wid1)
                LOG.debug("Response from CLI: " + str(out))

                if (cli_parser.cli_response_parser(out, 'encryption') == "True" and cli_parser.cli_response_parser(out, 'id') == self.wid1):
                    reporting.add_test_step(
                        "workload-show command encryption value is true", tvaultconf.PASS)
                    LOG.debug("Command executed correctly")
                else:
                    reporting.add_test_step(
                        "workload-show command encryption value is false", tvaultconf.FAIL)
                    # raise Exception("Command did not execute correctly : " + str(rc))
                    LOG.debug("Command not executed correctly")

            # Create workload with CLI with no sceret uuid
            workload_create_with_encryption = command_argument_string.workload_create_with_encryption + \
                                              " instance-id=" + str(self.vm_id)
            error = cli_parser.cli_error(workload_create_with_encryption)
            if error and (str(error.strip('\n')).find('ERROR') != -1):
                LOG.debug("workload with encryption creation unsuccessful for no secret")
                reporting.add_test_step("Create encrypted workload cli failed for no secret UUID",
                                        tvaultconf.PASS)
                tests[0][1] = 1
                reporting.test_case_to_write()
            else:
                LOG.debug("workload with encryption created successfully for no secret")
                raise Exception("Create encrypted workload cli created with no secret UUID")

            reporting.add_test_script(tests[1][0])
            # Create workload with API
            try:
                self.wid = self.workload_create([self.vm_id],
                                                encryption=True,
                                                secret_uuid=str(self.secret_uuid))
                reporting.add_test_step("Create multiple encrypted workloads with same secret UUID", tvaultconf.FAIL)
            except Exception as e:
                LOG.debug(f"Exception: {e}")
                reporting.add_test_step("Create multiple encrypted workloads with same secret UUID", tvaultconf.PASS)
                tests[1][1] = 1
                reporting.test_case_to_write()

            reporting.add_test_script(tests[2][0])
            # Create workload with API
            try:
                self.wid = self.workload_create([self.vm_id],
                                                encryption=True,
                                                secret_uuid="invalid")
                reporting.add_test_step("Create encrypted workload api created for invalid secret UUID", tvaultconf.FAIL)
            except Exception as e:
                LOG.debug(f"Exception: {e}")
                reporting.add_test_step("Create encrypted workload api failed for invalid secret UUID", tvaultconf.PASS)

            # Create workload with CLI
            workload_create_with_encryption = command_argument_string.workload_create_with_encryption + \
                                              " instance-id=" + str(self.vm_id) + \
                                              " --secret-uuid " + "invalid"
            error = cli_parser.cli_error(workload_create_with_encryption)
            if error and (str(error.strip('\n')).find('ERROR') != -1):
                LOG.debug("workload with encryption creation unsuccessful for invalid secret")
                reporting.add_test_step("Create encrypted workload cli failed for invalid secret UUID", tvaultconf.PASS)
                tests[2][1] = 1
                reporting.test_case_to_write()
            else:
                LOG.debug("workload with encryption created successfully for invalid secret")
                raise Exception("Create encrypted workload cli created with invalid secret UUID")


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
            # Delete workload
            self.workload_delete(self.wid1)

    # Workload policy with scheduler and retention parameter
    @test.pre_req({'type': 'barbican_workload'})
    @decorators.attr(type='workloadmgr_cli')
    def test_07_barbican(self):
        reporting.add_test_script(str(__name__) + "_Create_encrypted_workload_with_workload_policy")
        try:
            if self.exception != "":
                LOG.debug("pre req failed")
                reporting.add_test_step(str(self.exception), tvaultconf.FAIL)
                raise Exception(str(self.exception))
            LOG.debug("pre req completed")
            snapshots_list = []

            # Create workload policy
            policy_id = self.workload_policy_create(
                interval=tvaultconf.interval, policy_cleanup=True)
            if policy_id != "":
                reporting.add_test_step(
                    "Create workload policy", tvaultconf.PASS)
                LOG.debug("Workload policy id is " + str(policy_id))
            else:
                reporting.add_test_step(
                    "Create workload policy", tvaultconf.FAIL)
                raise Exception(
                    "Workload policy has not been created")

            # Verify policy is created
            policy_list = self.get_policy_list()
            if policy_id in policy_list:
                reporting.add_test_step(
                    "Verify policy created", tvaultconf.PASS)
                LOG.debug("Policy is created")
            else:
                reporting.add_test_step(
                    "Verify policy created", tvaultconf.FAIL)
                raise Exception("Policy is not creaed")

            # Assign workload policy to projects
            project_id = CONF.identity.tenant_id
            status = self.assign_unassign_workload_policy(
                str(policy_id), add_project_ids_list=[project_id], remove_project_ids_list=[])
            LOG.debug("Policy is assigned")
            self.mount_path = self.get_mountpoint_path()

            # Create workload with policy by CLI command
            workload_create_with_encryption = command_argument_string.workload_create_with_encryption + \
                                              " instance-id=" + str(self.vm_id) + \
                                              " --secret-uuid " + str(self.secret_uuid) + \
                                              " --policy-id " + str(policy_id)
            LOG.debug("workload_create_with_encryption : " + workload_create_with_encryption)
            error = cli_parser.cli_error(workload_create_with_encryption)
            LOG.debug("Workload created: " + error)
            if error and (str(error.strip('\n')).find('ERROR') != -1):
                reporting.add_test_step(
                    "Execute workload-create with policy command",
                    tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-create with policy command",
                    tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            time.sleep(10)
            self.workload_id = query_data.get_workload_id_in_creation(tvaultconf.workload_name)
            LOG.debug("Created workload ID: " + str(self.workload_id))
            if (self.workload_id != ""):
                self.wait_for_workload_tobe_available(self.workload_id)
                if (self.getWorkloadStatus(self.workload_id) == "available"):
                    reporting.add_test_step(
                        "Create workload with policy", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Create workload with policy", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Create workload with policy", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # Verify that workload is created with same policy ID
            workload_details = self.get_workload_details(self.workload_id)
            policyid_from_workload_metadata = workload_details["metadata"]["policy_id"]
            if policyid_from_workload_metadata == policy_id:
                reporting.add_test_step(
                    "Verfiy that same policy id is assigned in workload-metadata",
                    tvaultconf.PASS)
                LOG.debug("Same policy id is assigned in workload-metadata")
            else:
                reporting.add_test_step(
                    "Verfiy that same policy id is assigned in workload-metadata",
                    tvaultconf.FAIL)
                raise Exception(
                    "policy id not assigned properly in workload-metadata")

            # Verify workload created with scheduler enable
            status = self.getSchedulerStatus(self.workload_id)
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

            # Get retention parameters values of wid wirh scheduler enabled
            retention_policy_type_wid = self.getRetentionPolicyTypeStatus(
                self.workload_id)
            retention_policy_value_wid = self.getRetentionPolicyValueStatus(
                self.workload_id)
            Full_Backup_Interval_Value_wid = self.getFullBackupIntervalStatus(
                self.workload_id)

            # retention meets as mentioned value in the workload policy
            # Create snapshots equal to number of retention_policy_value
            for i in range(0, int(retention_policy_value_wid)):
                snapshot_id = self.workload_snapshot(
                    self.workload_id,
                    True,
                    snapshot_name=tvaultconf.snapshot_name +
                                  str(i),
                    snapshot_cleanup=False)
                snapshots_list.append(snapshot_id)
            LOG.debug("snapshot id list is : " + str(snapshots_list))

            # Create one more snapshot
            snapshot_id = self.workload_snapshot(
                self.workload_id,
                True,
                snapshot_name=tvaultconf.snapshot_name +
                              "_final",
                snapshot_cleanup=True)
            LOG.debug("Last snapshot id is : " + str(snapshot_id))

            self.wait_for_snapshot_tobe_available(
                self.workload_id, snapshot_id)
            LOG.debug("wait for snapshot available state")

            snapshots_list.append(snapshot_id)
            LOG.debug("final snapshot list is " + str(snapshots_list))

            # get snapshot count and snapshot_details
            snapshot_list_of_workload = self.getSnapshotListWithNoError(self.workload_id)
            LOG.debug("snapshot list of workload retrieved using API is : " +
                      str(snapshot_list_of_workload))

            # verify that numbers of snapshot created persist
            # retention_policy_value
            LOG.debug("number of snapshots created : %d " %
                      len(snapshot_list_of_workload))
            if int(retention_policy_value_wid) == len(
                    snapshot_list_of_workload):
                reporting.add_test_step(
                    "Verify number of snapshots created equals retention_policy_value",
                    tvaultconf.PASS)
                LOG.debug(
                    "Number of snapshots created equals retention_policy_value")
            else:
                reporting.add_test_step(
                    "Verify number of snapshots created equals retention_policy_value",
                    tvaultconf.FAIL)
                raise Exception(
                    "Number of snapshots created not equal to retention_policy_value")

            # Check first snapshot is deleted or not after retention value
            # exceed
            deleted_snapshot_id = snapshots_list[0]
            LOG.debug("snapshot id of first snapshot is : " +
                      str(deleted_snapshot_id))
            if deleted_snapshot_id in snapshot_list_of_workload:
                reporting.add_test_step(
                    "Verify first snapshot deleted after retention value exceeds",
                    tvaultconf.FAIL)
                raise Exception(
                    "first snapshot not deleted after retention value exceeds")
            else:
                reporting.add_test_step(
                    "Verify first snapshot deleted after retention value exceeds",
                    tvaultconf.PASS)
                LOG.debug("first snapshot deleted after retention value exceeds")

            # Check first snapshot is deleted from backup target when retention
            # value exceed
            is_snapshot_exist = self.check_snapshot_exist_on_backend(
                self.mount_path, self.workload_id, deleted_snapshot_id)
            LOG.debug("Snapshot does not exist : %s" % is_snapshot_exist)
            if not is_snapshot_exist:
                LOG.debug("First snapshot is deleted from backup target")
                reporting.add_test_step(
                    "First snapshot deleted from backup target",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "First snapshot deleted from backup target",
                    tvaultconf.FAIL)
                raise Exception(
                    "First snapshot is not deleted from backup target media")


        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()
            # Cleanup
            # Delete snapshot
            snapshot_list_of_workload = self.getSnapshotList(self.workload_id)
            for i in range(0, len(snapshot_list_of_workload)):
                self.snapshot_delete(
                    self.workload_id, snapshot_list_of_workload[i])

            # Delete workload
            self.workload_delete(self.workload_id)

    #OS-2014 -
    #Create VM and attach encrypted volume to it.
    #Try to create a workload with encryption checkbox disabled and try to attach to above vm created.
    #Result - Workload creation should fail with proper error.
    @decorators.attr(type='workloadmgr_api')
    def test_08_barbican(self):
        try:
            test_var = "tempest.api.workloadmgr.barbican.test_"
            tests = [[test_var + "create_unencrypted_workload_with_encrypted_volume", 0]]
            reporting.add_test_script(tests[0][0])

            #create key pair...
            self.kp = self.create_key_pair(tvaultconf.key_pair_name)

            #create vm...
            self.vm_id = self.create_vm(key_pair=self.kp)

            #find volume_type = luks. So that existing encrypted volume type can be used.
            #Get the volume_type_id
            vol_type_id = -1
            for vol in CONF.volume.volume_types:
                if (vol.lower().find("luks") != -1):
                    vol_type_id = CONF.volume.volume_types[vol]

            if (vol_type_id == -1):
                raise Exception("No luks volume found to create encrypted volume. Test cannot be continued")

            #Now create volume with derived volume type id...
            self.volume_id = self.create_volume(
                volume_type_id=vol_type_id)

            LOG.debug("Volume ID: " + str(self.volume_id))

            self.volumes = []
            self.volumes.append(self.volume_id)
            #Attach volume to vm...
            self.attach_volume(self.volume_id, self.vm_id)
            LOG.debug("Encrypted Volume attached to vm: " + str(self.vm_id))

            #create a workload with encryption status as disabled and try to attach it to vm...
            try:
                workload_id = self.workload_create([self.vm_id],
                                                encryption=False,
                                                workload_cleanup=True)

                LOG.debug("Workload ID: " + str(workload_id))
                reporting.add_test_step("Unencrypted Workload creation with encrypted volume is created.", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            except Exception as e:
                LOG.error("Exception: " + str(e))
                err_msg = ["Unencrypted workload cannot have instance", "with encrypted Volume"]
                # look for all sub-string in error message.
                result = all(x in e.message for x in err_msg)
                if (result):
                    reporting.add_test_step("Unencrypted Workload cannot have instance with encrypted volume",
                                            tvaultconf.PASS)
                    reporting.set_test_script_status(tvaultconf.PASS)
                else:
                    reporting.add_test_step("Different execption occurred than expected.", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()
    #End of test case OS-2014

    #OS-2020 -
    #Create workload without encryption having vm with non encrypted volume attached.
    #take snapshot
    #do workload edit and add 1 more vm having encrypted volume attached
    #output - workload edit should fail...
    @decorators.attr(type='workloadmgr_cli')
    def test_09_barbican(self):
        try:
            test_var = "tempest.api.workloadmgr.barbican.test_"
            tests = [[test_var + "workload_edit_with_unencrypted_and_encrypted_volume", 0]]
            reporting.add_test_script(tests[0][0])

            # create key pair...
            kp = self.create_key_pair(tvaultconf.key_pair_name)

            # create vm...
            vm_id = self.create_vm(key_pair=kp)

            # find volume_type = encrypted and unencrypted.
            # Get the volume_type_id
            encrypted_vol_type = -1
            unencrypted_vol_type = -1
            for vol in CONF.volume.volume_types:
                if (vol.lower().find("luks") != -1):
                    encrypted_vol_type = CONF.volume.volume_types[vol]
                elif (vol.lower().find("multiattach") == -1):
                    unencrypted_vol_type = CONF.volume.volume_types[vol]

            if (encrypted_vol_type == -1):
                reporting.add_test_step("Encrypted volume type is missing." \
                                        "openstack-setup.conf should have luks volume types like - luks-lvm, luks-ceph, luks etc." \
                                        "Cannot continue with the test...", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("No luks volume type found to create encrypted volume.")

            if (unencrypted_vol_type == -1):
                reporting.add_test_step("Unecrypted volume type is missing." \
                                        "openstack-setup.conf should have volume types like - lvm, ceph, rbd etc." \
                                        "Cannot continue with the test...", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("No volume type like lvm, ceph, rbd etc. found to create unencrypted volume.")

            # Now create volume with derived volume type id...
            volume_id = self.create_volume(
                volume_type_id=unencrypted_vol_type)

            # Attach volume to vm...
            self.attach_volume(volume_id, vm_id)

            # create a workload with encryption status as disabled and try to attach it to vm...
            try:
                wid = self.workload_create([vm_id],
                                           encryption=False,
                                           workload_cleanup=True)

                LOG.debug("Workload ID: " + str(wid))
                reporting.add_test_step("Unencrypted workload creation with unencrypted volume is successful.",
                                        tvaultconf.PASS)
                reporting.set_test_script_status(tvaultconf.PASS)

            except Exception as e:
                LOG.error("Exception: " + str(e))
                reporting.add_test_step("Unencrypted Workload creation with unencrypted volume is failed to create.",
                                        tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("Unencrypted workload creation failed.")

            # create snapshot of workload created...
            snapshot_id = self.workload_snapshot(wid, True)

            self.wait_for_workload_tobe_available(wid)
            snapshot_status = self.getSnapshotStatus(wid, snapshot_id)

            if (snapshot_status == "available"):
                LOG.debug("Full snapshot created...")
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                reporting.set_test_script_status(tvaultconf.PASS)
            else:
                reporting.add_test_step("Create full snapshot", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("Create full snapshot failed")

            # now create another vm with encrypted volume...
            # create another key pair...
            kp1 = self.create_key_pair(tvaultconf.key_pair_name)

            # create another vm...
            vm_id1 = self.create_vm(key_pair=kp1)

            # Now create volume with derived volume type id...
            volume_id1 = self.create_volume(
                volume_type_id=encrypted_vol_type)

            # Attach volume to vm...
            self.attach_volume(volume_id1, vm_id1)

            # now edit the workload with workload_modify cli and try to attach vm with encrypted volume...
            try:
                workload_modify_command = command_argument_string.workload_modify + "--instance instance-id=" + \
                                          str(vm_id1) + " --instance instance-id=" + str(vm_id) + " " + str(wid)

                error = cli_parser.cli_error(workload_modify_command)
                if error:
                    err_msg = ["Unencrypted workload cannot have instance", "with encrypted Volume"]
                    result = all(x in error for x in err_msg)
                    if (result):
                        reporting.add_test_step("Unencrypted Workload cannot have instance with encrypted volume",
                            tvaultconf.PASS)
                        reporting.set_test_script_status(tvaultconf.PASS)
                    else:
                        reporting.add_test_step("Different execption occurred.", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)
                else:
                    # If no error is thrown then we should check for return code and vm count.
                    rc = cli_parser.cli_returncode(workload_modify_command)
                    if rc != 0:
                        reporting.add_test_step(
                            "Unencrypted Workload cannot have instance with encrypted volume",
                            tvaultconf.PASS)
                        reporting.set_test_script_status(tvaultconf.PASS)
                    else:
                        self.wait_for_workload_tobe_available(wid)
                        # check for vm count - If it is more than 1 then test case failed...
                        workload_vm_count = query_data.get_available_vms_of_workload(wid)

                        if (workload_vm_count == 2):
                            reporting.add_test_step("Unencrypted workload connected with another instance with encrypted volume",
                                tvaultconf.FAIL)
                            reporting.set_test_script_status(tvaultconf.FAIL)
                        else:
                            reporting.add_test_step("Unencrypted Workload cannot have instance with encrypted volume.", tvaultconf.PASS)
                            reporting.set_test_script_status(tvaultconf.PASS)

            except Exception as e:
                LOG.error("Exception: " + str(e))
                reporting.add_test_step(str(e), tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()

    # End of test case OS-2020

    #OS-2024 -
    #Create VM and attach unencrypted volume to it.
    #Create unencrypted workload of that instance.
    #Create encrypted volume and attach to instance
    #take a full snapshot and verify the result.
    #Result - full snapshot creation should fail.
    @decorators.attr(type='workloadmgr_api')
    def test_10_barbican(self):
        try:
            test_var = "tempest.api.workloadmgr.barbican.test_"
            tests = [[test_var + "create_full_snapshot_with_encrypted_and_unencrypted_volume_instance", 0]]
            reporting.add_test_script(tests[0][0])

            #create key pair...
            self.kp = self.create_key_pair(tvaultconf.key_pair_name)

            #create vm...
            vm_id = self.create_vm(key_pair=self.kp)

            # find volume_type = encrypted and unencrypted.
            # Get the volume_type_id
            encrypted_vol_type = -1
            unencrypted_vol_type = -1
            for vol in CONF.volume.volume_types:
                if (vol.lower().find("luks") != -1):
                    encrypted_vol_type = CONF.volume.volume_types[vol]
                elif (vol.lower().find("multiattach") == -1):
                    unencrypted_vol_type = CONF.volume.volume_types[vol]

            if (encrypted_vol_type == -1):
                reporting.add_test_step("Encrypted volume type is missing." \
                                        "openstack-setup.conf should have luks volume types like - luks-lvm, luks-ceph, luks etc." \
                                        "Cannot continue with the test...", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("No luks volume type found to create encrypted volume.")

            if (unencrypted_vol_type == -1):
                reporting.add_test_step("Unecrypted volume type is missing." \
                                        "openstack-setup.conf should have volume types like - lvm, ceph, rbd etc." \
                                        "Cannot continue with the test...", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("No volume type like lvm, ceph, rbd etc. found to create unencrypted volume.")

            # Now create unencrypted volume with derived volume type id...
            volume_id = self.create_volume(
                volume_type_id=unencrypted_vol_type)

            # Attach volume to vm...
            self.attach_volume(volume_id, vm_id)
            LOG.debug("volume id attached : " + str(volume_id))

            # create a workload with encryption status as disabled and try to attach it to vm...
            wid = self.workload_create([vm_id],
                                       encryption=False,
                                       workload_cleanup=True)

            LOG.debug("Workload ID: " + str(wid))

            if (wid is not None):
                self.wait_for_workload_tobe_available(wid)
                if (self.getWorkloadStatus(wid) == "available"):
                    reporting.add_test_step("Create unencrypted workload",
                                            tvaultconf.PASS)
                else:
                    reporting.add_test_step("Create unencrypted workload",
                                            tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
                    raise Exception("Unencrypted Workload creation failed")
            else:
                reporting.add_test_step("Create unencrypted workload",
                                        tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("Unencrypted Workload creation failed")

            # Now create an encrypted volume with derived volume type id...
            volume_id1 = self.create_volume(
                volume_type_id=encrypted_vol_type)

            # Attach volume to existing vm instance...
            self.attach_volume(volume_id1, vm_id)
            LOG.debug("encrypted volume id attached : " + str(volume_id1))

            total_volumes = self.get_attached_volumes(vm_id)
            LOG.debug("total number of vols: " + str(total_volumes))
            if len(total_volumes) == 2:
                reporting.add_test_step("Attach Encrypted volume to existing instance", tvaultconf.PASS)
                reporting.set_test_script_status(tvaultconf.PASS)
            else:
                reporting.add_test_step("Attach Encrypted volume to existing instance", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("Encrypted volume failed to attach existing instance")

            # create snapshot of workload created...
            snapshot_id = self.workload_snapshot(wid, True)

            self.wait_for_workload_tobe_available(wid)
            snapshot_status = self.getSnapshotStatus(wid, snapshot_id)

            if (snapshot_status == "available"):
                LOG.debug("Full snapshot created with unencrypted and encrypted volume.")
                reporting.add_test_step("Create full snapshot", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("Full snapshot created with unencrypted and encrypted volume")
            else:
                #get the created snapshot information
                snapshot_info = self.getSnapshotInfo(snapshot_id)
                error = snapshot_info[3]
                if error:
                    err_msg = ["Unencrypted workload cannot have instance", "with encrypted Volume"]
                    result  = all(x in error for x in err_msg)
                    if (result):
                        reporting.add_test_step("Unencrypted Workload cannot have instance with encrypted volume",
                            tvaultconf.PASS)
                    else:
                        LOG.error("Error: " + str(error))
                        reporting.add_test_step("Different error occurred.", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)
                else:
                    LOG.error("Error: " + str(error))
                    reporting.add_test_step("Different error occurred.", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()
    #End of test case OS-2024

    @test.pre_req({'type': 'small_workload'})
    @decorators.attr(type='workloadmgr_cli')
    def test_11_barbican(self):
        try:
            reporting.add_test_script(str(__name__) + \
                    "_validate_scheduler_trust_with_scheduler_enabled")
            if self.exception != "":
                LOG.error("pre req failed")
                raise Exception(str(self.exception))
            LOG.debug("pre req completed")
            global vm_id
            global volume_id
            global exception
            global secret_uuid
            vm_id = self.vm_id
            volume_id = self.volume_id
            exception = self.exception

            # Create scheduled encrypted workload
            self.secret_uuid = self.create_secret(secret_cleanup=True)
            secret_uuid = self.secret_uuid

            # Modify workload scheduler to enable and set the start date, time
            # and timezone
            now = datetime.datetime.utcnow()
            now_date = datetime.datetime.strftime(now, "%m/%d/%Y")
            now_time_plus_2 = now + datetime.timedelta(minutes=2)
            now_time_plus_2 = datetime.datetime.strftime(
                now_time_plus_2, "%I:%M %p")
            self.wid = self.workload_create([vm_id],
                        jobschedule={"start_date": now_date.strip(),
                            "start_time": now_time_plus_2.strip(),
                            "interval": tvaultconf.interval,
                            "retention_policy_type":
                                tvaultconf.retention_policy_type,
                            "retention_policy_value":
                                tvaultconf.retention_policy_value,
                            "enabled": "True"}, encryption=True,
                        secret_uuid=secret_uuid)
            LOG.debug("Workload ID: " + str(self.wid))
            self.wait_for_workload_tobe_available(self.wid)
            if(self.getWorkloadStatus(self.wid) == "available"):
                reporting.add_test_step(
                    "Create scheduled encrypted workload", tvaultconf.PASS)
            else:
                raise Exception("Create scheduled encrypted workload")

            #Execute scheduler-trust-validate CLI command
            self._execute_scheduler_trust_validate_cli()

            #Fetch trust list from API
            trust_list = self.get_trusts()

            #Verify if trust details returned in steps 3 and 4 match
            found = False
            for trust in trust_list:
                if trust['name'] == self.wlm_trust['name']:
                    found = True
                    break
            if found and self.wlm_trust_valid and self.wlm_scheduler:
                reporting.add_test_step("Verify valid trust", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify valid trust", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            #Delete the trust using API
            if self.delete_trust(self.wlm_trust['name']):
                reporting.add_test_step("Delete trust", tvaultconf.PASS)
            else:
                raise Exception("Delete trust")

            #Execute scheduler-trust-validate CLI for workload WL-1
            self._execute_scheduler_trust_validate_cli()

            #Verify if trust details are returned appropriately
            if not self.wlm_trust and not self.wlm_trust_valid and \
                    self.wlm_scheduler:
                reporting.add_test_step("Verify broken trust", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify broken trust", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            #Create the trust again using API
            role = ','.join(tvaultconf.trustee_role)
            trust_id = self.create_trust(role)
            if trust_id:
                reporting.add_test_step("Create user trust on project", tvaultconf.PASS)
            else:
                raise Exception("Create user trust on project")

            #Execute scheduler-trust-validate CLI for workload WL-1
            self._execute_scheduler_trust_validate_cli()

            #Verify if trust details are returned appropriately
            trust_list = self.get_trusts()
            found = False
            for trust in trust_list:
                if trust['name'] == self.wlm_trust['name']:
                    found = True
                    break
            if found and self.wlm_trust_valid and self.wlm_scheduler:
                reporting.add_test_step("Verify valid trust", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify valid trust", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_12_barbican(self):
        try:
            reporting.add_test_script(str(__name__) + \
                    "_validate_scheduler_trust_with_scheduler_disabled")
            global vm_id
            global volume_id
            global exception
            global secret_uuid
            if exception != "":
                LOG.error("pre req failed")
                raise Exception(str(exception))
            LOG.debug("pre req completed")

            # Create workload with scheduler disabled using CLI
            time.sleep(10)
            workload_create = \
                    command_argument_string.workload_create_with_encryption +\
                " instance-id=" + \
                str(vm_id) + " --jobschedule enabled=False" + \
                " --secret-uuid " + str(secret_uuid)
            rc = cli_parser.cli_returncode(workload_create)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-create command with scheduler disable",
                    tvaultconf.FAIL)
                raise Exception(
                    "Command workload create did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-create command with scheduler disable",
                    tvaultconf.PASS)

            time.sleep(10)
            self.wid = query_data.get_workload_id_in_creation(tvaultconf.workload_name)
            LOG.debug("Workload ID: " + str(self.wid))
            timer = 0
            while (self.wid is None):
                time.sleep(10)
                self.wid = query_data.get_workload_id_in_creation(tvaultconf.workload_name)
                timer = timer + 1
                if(self.wid is not None):
                    self.wait_for_workload_tobe_available(self.wid)
                    if(self.getWorkloadStatus(self.wid) == "available"):
                        reporting.add_test_step(
                            "Create workload with scheduler disable", tvaultconf.PASS)
                    else:
                        reporting.add_test_step(
                            "Create workload with scheduler disable", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)
                elif(timer >= 12):
                    raise Exception("Create workload with scheduler disabled")

            #Execute scheduler-trust-validate CLI command
            self._execute_scheduler_trust_validate_cli()

            #Fetch trust list from API
            trust_list = self.get_trusts()

            #Verify trust details returned
            if not self.wlm_trust_valid and \
                    not self.wlm_scheduler and \
                    len(trust_list) > 0:
                reporting.add_test_step("Verify trust", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify trust", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            #Delete the trust using API
            if self.delete_trust(trust_list[0]['name']):
                reporting.add_test_step("Delete trust", tvaultconf.PASS)
            else:
                raise Exception("Delete trust")

            #Execute scheduler-trust-validate CLI for workload WL-1
            self._execute_scheduler_trust_validate_cli()

            #Verify if trust details are returned appropriately
            if not self.wlm_trust and \
                    not self.wlm_trust_valid and \
                    not self.wlm_scheduler:
                reporting.add_test_step("Verify trust", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify trust", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            #Create the trust again using API
            role = ','.join(tvaultconf.trustee_role)
            trust_id = self.create_trust(role)
            if trust_id:
                reporting.add_test_step("Create user trust on project", tvaultconf.PASS)
            else:
                raise Exception("Create user trust on project")

        except Exception as e:
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            self.workload_delete(self.wid)
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_13_cleanup(self):
        try:
            global vm_id
            global volume_id
            global secret_uuid
            self.delete_vm(vm_id)
            self.delete_volume(volume_id)
            self.delete_secret(secret_uuid)
        except Exception as e:
            LOG.error(f"Exception in test_13_cleanup: {e}")

    #OS-2018 -
    #Create secret with empty payload.
    #Create encrypted workload with above secret UUID.
    #Result - Workload creation should fail as secert UUID should map to payload
    @decorators.attr(type='workloadmgr_cli')
    def test_14_barbican(self):
        try:
            reporting.add_test_script(str(__name__) + "_create_secret_with_empty_payload")

            # create key pair...
            self.kp = self.create_key_pair(tvaultconf.key_pair_name)

            # create vm...
            self.vm_id = self.create_vm(key_pair=self.kp)

            # create secret with empty payload
            secret_key_cmd = command_argument_string.openstack_create_secret_with_empty_payload
            LOG.debug("secret key cmd: " + str(secret_key_cmd))

            # parse the output to get the secret uuid.
            out = cli_parser.cli_output(secret_key_cmd)
            LOG.debug("Response from CLI: " + str(out))

            # load the json data
            if out and (str(out).find('Secret href') != -1):
                reporting.add_test_step(
                    "Create secret with an empty payload.",
                    tvaultconf.PASS)
                result = (json.loads(out))
                out = result['Secret href']
                out = out.split('/secrets/')[1].strip('.')
                self.secret_uuid = out.replace(" ", "")
            else:
                raise Exception("Create secret with an empty payload.")

            LOG.debug("secret uuid to pass for workload instance creation: " + str(self.secret_uuid))

            # Create workload with CLI
            workload_create_with_encryption = command_argument_string.workload_create_with_encryption + \
                                              " instance-id=" + str(self.vm_id) + \
                                              " --secret-uuid " + str(self.secret_uuid)

            error = cli_parser.cli_error(workload_create_with_encryption)
            if error and (str(error.strip('\n')).find('ERROR') != -1):
                LOG.debug("Error: " + str(error))
                err_msg = ["Either the secret UUID or the payload of the secret is invalid"]
                result = all(x in error for x in err_msg)
                if (result):
                    reporting.add_test_step("Creation of workload instance cannot have an empty payload",
                                            tvaultconf.PASS)
                    reporting.set_test_script_status(tvaultconf.PASS)
                else:
                    reporting.add_test_step("Different error occurred.",
                                            tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                LOG.debug("workload with encryption created successfully")
                reporting.add_test_step("workload instance with secret uuid of an empty payload",
                                        tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

                time.sleep(10)
                # workload created successfully, we need to delete it. Get the workload id...
                self.wid1 = query_data.get_workload_id_in_creation(
                    tvaultconf.workload_name)
                workload_available = self.wait_for_workload_tobe_available(
                    self.wid1)
                LOG.debug("Workload ID: " + str(self.wid1))

                # Delete workload
                self.workload_delete(self.wid1)

            # if we come down here, we need to cleanup the secret uuid created...
            self.delete_secret(self.secret_uuid)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()
    # End of test case OS-2018

    @decorators.attr(type='workloadmgr_api')
    def test_15_barbican(self):
        reporting.add_test_script(str(__name__) + "_Workload_reset_on_encrypted_workload")
        try:
            self.snapshot_ids = []

            # create key pair...
            self.kp = self.create_key_pair(tvaultconf.key_pair_name)

            # create vm...
            vm_id = self.create_vm(key_pair=self.kp)

            # Create secret UUID
            secret_uuid = self.create_secret()

            # find volume_type = encrypted and unencrypted.
            # Get the volume_type_id
            encrypted_vol_type = -1
            unencrypted_vol_type = -1
            for vol in CONF.volume.volume_types:
                if (vol.lower().find("luks") != -1):
                    encrypted_vol_type = CONF.volume.volume_types[vol]
                elif (vol.lower().find("multiattach") == -1):
                    unencrypted_vol_type = CONF.volume.volume_types[vol]

            if (encrypted_vol_type == -1):
                reporting.add_test_step("Encrypted volume type is missing." \
                                        "openstack-setup.conf should have luks volume types like - luks-lvm, luks-ceph, luks etc." \
                                        "Cannot continue with the test...", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("No luks volume type found to create encrypted volume.")

            if (unencrypted_vol_type == -1):
                reporting.add_test_step("Unecrypted volume type is missing." \
                                        "openstack-setup.conf should have volume types like - lvm, ceph, rbd etc." \
                                        "Cannot continue with the test...", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("No volume type like lvm, ceph, rbd etc. found to create unencrypted volume.")

            # Now create unencrypted volume with derived volume type id...
            volume_id = self.create_volume(
                volume_type_id=unencrypted_vol_type)

            # Attach volume to vm...
            self.attach_volume(volume_id, vm_id)
            LOG.debug("volume id attached : " + str(volume_id))

            # Now create encrypted volume with derived volume type id...
            encrypt_volume_id = self.create_volume(
                volume_type_id=encrypted_vol_type)

            LOG.debug("Encrypted Volume ID: " + str(encrypt_volume_id))

            self.volumes = []
            self.volumes.append(volume_id)
            self.volumes.append(encrypt_volume_id)
            # Attach volume to vm...
            self.attach_volume(encrypt_volume_id, vm_id)
            LOG.debug("Encrypted Volume attached to vm: " + str(vm_id))

            # create a workload
            workload_id = self.workload_create([vm_id],
                                               encryption=True,
                                               secret_uuid=secret_uuid)

            LOG.debug("Workload ID: " + str(workload_id))
            reporting.add_test_step("Encrypted Workload with encrypted and non encrypted volume is created.",
                                    tvaultconf.PASS)

            # Create full snapshot
            self.snapshot_id_full = self.workload_snapshot(
                workload_id, True)
            self.wait_for_workload_tobe_available(workload_id)
            if (self.getSnapshotStatus(workload_id, self.snapshot_id_full) != "available"):
                self.exception = "Create full snapshot"
                raise Exception(str(self.exception))

            self.snapshot_ids.append(self.snapshot_id_full)

            LOG.debug("Snapshot ID-1: " + str(self.snapshot_ids[0]))
            reporting.add_test_step("Full Snapshot is created.",
                                    tvaultconf.PASS)


            # Create incremental-1 snapshot
            self.snapshot_id_inc = self.workload_snapshot(
                workload_id, False)
            self.wait_for_workload_tobe_available(workload_id)
            if (self.getSnapshotStatus(workload_id, self.snapshot_id_inc) != "available"):
                self.exception = "Create incremental-1 snapshot"
                raise Exception(str(self.exception))

            self.snapshot_ids.append(self.snapshot_id_inc)
            LOG.debug("Snapshot ID-2: " + str(self.snapshot_ids[1]))
            reporting.add_test_step("Incremental Snapshot is created.",
                                    tvaultconf.PASS)

            volume_snapshots1 = self.get_volume_snapshots(volume_id)
            LOG.debug("Volumes snapshots for: " +
                      str(volume_id) + ": " + str(volume_snapshots1))
            if len(volume_snapshots1) == 1:
                reporting.add_test_step("Unencrypted Volume snapshot count is 1", tvaultconf.PASS)
            else:
                reporting.add_test_step("Unencrypted Volume snapshot count is not 1", tvaultconf.FAIL)
                raise Exception("Unencrypted Volume snapshot count is not 1")

            volume_snapshots2 = self.get_volume_snapshots(encrypt_volume_id)
            LOG.debug("Volumes snapshots for: " +
                      str(encrypt_volume_id) + ": " + str(volume_snapshots2))
            if len(volume_snapshots2) == 1:
                reporting.add_test_step("Encrypted Volume snapshot count is 1", tvaultconf.PASS)
            else:
                reporting.add_test_step("Encrypted Volume snapshot count is not 1", tvaultconf.FAIL)
                raise Exception("Encrypted Volume snapshot count is not 1")

            workload_reset_status = self.workload_reset(workload_id)
            if workload_reset_status:
                reporting.add_test_step("Workload reset request raised", tvaultconf.PASS)
            else:
                LOG.error("Workload reset request failed")
                reporting.add_test_step("Workload reset request failed", tvaultconf.FAIL)
                raise Exception("Workload reset request failed")

            start_time = time.time()
            time.sleep(10)
            volsnaps_after = self.get_volume_snapshots(volume_id)
            while (len(volsnaps_after) != 0 and (time.time() - start_time < 600)):
                volsnaps_after = self.get_volume_snapshots(volume_id)
                time.sleep(5)
            if len(volsnaps_after) == 0:
                reporting.add_test_step("Temp Volume snapshot is deleted after workload reset", tvaultconf.PASS)
            else:
                reporting.add_test_step("Temp Volume snapshot not deleted after workload reset", tvaultconf.FAIL)
                raise Exception("Workload reset failed as temp volume snapshot is not deleted")
            volsnaps_after1 = self.get_volume_snapshots(encrypt_volume_id)
            if len(volsnaps_after1) == 0:
                reporting.add_test_step("Encrypted Volume snapshot is deleted after workload reset", tvaultconf.PASS)
            else:
                reporting.add_test_step("Encrypted Volume snapshot not deleted after workload reset", tvaultconf.FAIL)
                raise Exception("Workload reset failed as Encrypted volume snapshot is not deleted")

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    # Test case automated #OS-2025
    # http://192.168.15.51/testlink/linkto.php?tprojectPrefix=OS&item=testcase&id=OS-2025
    @decorators.attr(type='workloadmgr_api')
    def test_16_barbican(self):
        try:
            test_var = "tempest.api.workloadmgr.barbican.with_secret_order_"
            tests = [[test_var+"create_secret", 0],
                    [test_var+"workload_api", 0],
                    [test_var+"full_snapshot_api", 0],
                    [test_var+"incremental_snapshot_api", 0],
                    [test_var+"snapshot_mount_api", 0],
                    [test_var+"filesearch_api", 0],
                    [test_var+"selectiverestore_api", 0],
                    [test_var+"inplacerestore_api", 0],
                    [test_var+"oneclickrestore_api", 0]]

            reporting.add_test_script(tests[0][0])
            try:
                self.order_uuid = self.create_secret_order("sec_order1")
                LOG.debug("Created secret order: {}".format(self.order_uuid))
                time.sleep(10)
                self.secret_uuid = self.get_secret_from_order(self.order_uuid)
                LOG.debug("Getting secret key from secret order: {}".format(self.secret_uuid))
                reporting.add_test_step("Creating secret key using secret order", tvaultconf.PASS)
                tests[0][1] = 1
                reporting.test_case_to_write()
            except Exception as e:
                LOG.error(f"Exception: {e}")
                raise Exception("Getting secret key from secret order")

            reporting.add_test_script(tests[1][0])
            self.kp = self.create_key_pair(tvaultconf.key_pair_name)
            self.vm_id = self.create_vm(key_pair=self.kp)
            self.volumes = []
            self.disk_names = ["vda"]
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
            self._set_frm_user()
            LOG.debug("FRM Instance ID: " + str(self.frm_id))
            self.set_floating_ip(fip[1], self.frm_id)

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.install_qemu(ssh)
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 3)
            md5sums_before_full = self._get_md5sum(ssh, ["/opt"])
            LOG.debug(f"md5sums_before_full: {md5sums_before_full}")
            ssh.close()
            self.mount_path = self.get_mountpoint_path()

            # Create workload with API
            try:
                self.wid = self.workload_create([self.vm_id],
                        encryption=True,
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
                    tests[1][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Create encrypted workload "\
                         "with image booted vm")
            else:
                raise Exception("Create encrypted workload with image "\
                        "booted vm")

            reporting.add_test_script(tests[2][0])
            self.snapshot_id = self.workload_snapshot(self.wid, True)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id)
            if(self.snapshot_status == "available"):
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                        self.mount_path, self.wid, self.snapshot_id)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on "\
                            "target backend", tvaultconf.PASS)
                    self._check_encryption_on_backend(self.wid, self.snapshot_id,
                            self.vm_id, self.disk_names, self.mount_path)

                    tests[2][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create full snapshot")

            reporting.add_test_script(tests[3][0])
            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 5)
            md5sums_before_incr = self._get_md5sum(ssh, ["/opt"])
            LOG.debug(f"md5sums_before_incr: {md5sums_before_incr}")
            ssh.close()

            self.snapshot_id2 = self.workload_snapshot(self.wid, False)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id2)
            if(self.snapshot_status == "available"):
                reporting.add_test_step("Create incremental snapshot", tvaultconf.PASS)
                self.snapshot_found = self.check_snapshot_exist_on_backend(
                        self.mount_path, self.wid, self.snapshot_id2)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on "\
                            "target backend", tvaultconf.PASS)
                    self._check_encryption_on_backend(self.wid, self.snapshot_id2,
                            self.vm_id, self.disk_names, self.mount_path)

                    tests[3][1] = 1
                    reporting.test_case_to_write()
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create incremental snapshot")

            reporting.add_test_script(tests[4][0])
            # Mount full snapshot
            mount_status = self.mount_snapshot(
                self.wid, self.snapshot_id, self.frm_id, mount_cleanup=True)
            LOG.debug(f"mount_status for full snapshot: {mount_status}")
            if mount_status:
                reporting.add_test_step(
                    "Snapshot mount of full snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1],self.frm_ssh_user)
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
            else:
                reporting.add_test_step("Snapshot mount of full snapshot", tvaultconf.FAIL)

            unmount_status = self.unmount_snapshot(self.wid, self.snapshot_id)
            LOG.debug("VALUE OF is_unmounted: " + str(unmount_status))
            if unmount_status:
                reporting.add_test_step(
                   "Snapshot unmount of full snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                    fip[1], self.frm_ssh_user)
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
                self.wid, self.snapshot_id2, self.frm_id, mount_cleanup=True)
            if mount_status:
                reporting.add_test_step(
                    "Snapshot mount of incremental snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1], self.frm_ssh_user)
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
            else:
                reporting.add_test_step(
                    "Snapshot mount of incremental snapshot", tvaultconf.FAIL)

            unmount_status = self.unmount_snapshot(self.wid, self.snapshot_id2)
            LOG.debug("VALUE OF is_unmounted: " + str(unmount_status))
            if unmount_status:
                reporting.add_test_step(
                    "Snapshot unmount of incremental snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1], self.frm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh)
                ssh.close()

                if output_list == b'':
                    reporting.add_test_step(
                        "Unmount incremental snapshot", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Snapshot unmount of incremental snapshot", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Snapshot unmount of incremental snapshot", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
            tests[4][1] = 1

            #File search
            reporting.add_test_script(tests[5][0])
            filecount_in_snapshots = {
                self.snapshot_id: 0,
                self.snapshot_id2: 1}
            search_path = "/opt/File_4"
            self._filesearch(self.vm_id, filecount_in_snapshots, search_path)
            reporting.test_case_to_write()
            tests[5][1] = 1

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 6)
            md5sums_after_incr = self._get_md5sum(ssh, ["/opt"])
            LOG.debug(f"md5sums_after_incr: {md5sums_after_incr}")
            ssh.close()

            #selective restore
            reporting.add_test_script(tests[6][0])
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
                md5sums_after_full_selective = self._get_md5sum(ssh, ["/opt"])
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
                md5sums_after_incr_selective = self._get_md5sum(ssh, ["/opt"])
                LOG.debug(f"md5sums_after_incr_selective: {md5sums_after_incr_selective}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_selective:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Selective restore of incremental snapshot",
                        tvaultconf.FAIL)
            reporting.test_case_to_write()
            tests[6][1] = 1

            #Inplace restore for full snapshot
            reporting.add_test_script(tests[7][0])
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
                md5sums_after_full_inplace = self._get_md5sum(ssh, ["/opt"])
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
                md5sums_after_incr_inplace = self._get_md5sum(ssh, ["/opt"])
                LOG.debug(f"md5sums_after_incr_inplace: {md5sums_after_incr_inplace}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_inplace:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Inplace restore of incremental snapshot",
                        tvaultconf.FAIL)
            reporting.test_case_to_write()
            tests[7][1] = 1

            reporting.add_test_script(tests[8][0])
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
                md5sums_after_full_oneclick = self._get_md5sum(ssh, ["/opt"])
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
                md5sums_after_incr_oneclick = self._get_md5sum(ssh, ["/opt"])
                LOG.debug(f"md5sums_after_incr_oneclick: {md5sums_after_incr_oneclick}")
                ssh.close()

                if md5sums_before_incr == \
                        md5sums_after_incr_oneclick:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.PASS)
                    tests[8][1] = 1
                else:
                    LOG.debug("***MDSUMS DON'T MATCH***")
                    reporting.add_test_step(
                        "Md5 Verification for boot disk", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Oneclick restore of incremental snapshot",
                        tvaultconf.FAIL)
            reporting.test_case_to_write()

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

    # Test case automated #OS-2031 for attach volume ceph/rbd/tripleo
    # http://192.168.15.51/testlink/linkto.php?tprojectPrefix=OS&item=testcase&id=OS-2031
    @decorators.attr(type='workloadmgr_api')
    def test_17_barbican(self):
        test_var = "tempest.api.workloadmgr.barbican.rbd_device_cleanup.attach_ceph_volume_"
        restore_tests = [[test_var + "selectiverestore_api", "selective"], [test_var + "inplacerestore_api", "inplace"], [test_var + "oneclickrestore_api", "oneclick"]]

        for restore_test in restore_tests:
            try:
                reporting.add_test_script(restore_test[0])

                try:
                    order_uuid = self.create_secret_order("sec_order1")
                    LOG.debug("Created secret order: {}".format(order_uuid))
                    time.sleep(10)
                    secret_uuid = self.get_secret_from_order(order_uuid)
                    LOG.debug("Getting secret key from secret order: {}".format(secret_uuid))
                    reporting.add_test_step("Creating secret key using secret order", tvaultconf.PASS)
                except Exception as e:
                    LOG.error(f"Exception: {e}")
                    raise Exception("Getting secret key from secret order")

                vm_id = self.create_vm(vm_cleanup=True)
                # Get the details of luks-ceph (encrypted ceph) volumes from setup
                volume_type_id = ""
                for vol in CONF.volume.volume_types:
                    if (vol.lower().find("luks") != -1):
                        if (vol.lower().find("ceph") != -1) or (vol.lower().find("tripleo") != -1) or (
                                vol.lower().find("rbd") != -1):
                            volume_type_id = CONF.volume.volume_types[vol]
                            LOG.debug("Encrypted volume for ceph/rbd found : {}".format(volume_type_id))
                        elif (vol.lower() == "luks"):
                            volume_type_id = CONF.volume.volume_types[vol]
                            LOG.debug("Encrypted volume for ceph/rbd found : {}".format(volume_type_id))

                if not volume_type_id:
                    raise Exception("Exiting the test as encrypted ceph/rbd volume type is not found")

                vol_count = 2
                volumes = []
                disk_names = ["vda", "vdb", "vdc"]
                for i in range(vol_count):
                    volume_id = self.create_volume(
                        volume_type_id=volume_type_id)
                    volumes.append(volume_id)
                    self.attach_volume(volume_id, vm_id)
                LOG.debug(f"Volumes attached: {volumes}")
                self.mount_path = self.get_mountpoint_path()

                # Create workload with API
                wid = []
                try:
                    wid = self.workload_create([vm_id],
                                               encryption=True,
                                               secret_uuid=secret_uuid, workload_cleanup=True)
                    LOG.debug("Workload ID: " + str(wid))
                except Exception as e:
                    LOG.error(f"Exception: {e}")
                    raise Exception("Create encrypted workload with attached ceph volume")
                time.sleep(10)
                if (wid is not None):
                    self.wait_for_workload_tobe_available(wid)
                    self.workload_status = self.getWorkloadStatus(wid)
                    if (self.workload_status == "available"):
                        reporting.add_test_step("Created encrypted workload with attached ceph volume", tvaultconf.PASS)
                    else:
                        raise Exception("Create encrypted workload with attached ceph volume")
                else:
                    raise Exception("Create encrypted workload with attached ceph volume")

                snapshot_id = self.workload_snapshot(wid, True, snapshot_cleanup=True)
                self.wait_for_workload_tobe_available(wid)
                snapshot_status = self.getSnapshotStatus(wid, snapshot_id)
                if (snapshot_status == "available"):
                    reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                    snapshot_found = self.check_snapshot_exist_on_backend(
                        self.mount_path, wid, snapshot_id)
                    LOG.debug(f"snapshot_found: {snapshot_found}")
                    if snapshot_found:
                        reporting.add_test_step("Verify snapshot existence on " \
                                                "target backend", tvaultconf.PASS)
                        self._check_encryption_on_backend(wid, snapshot_id,
                                                          vm_id, disk_names, self.mount_path)
                    else:
                        raise Exception("Verify snapshot existence on target backend")
                else:
                    raise Exception("Create full snapshot")

                vol_snap_name = tvaultconf.triliovault_vol_snapshot_name

                # DB validations for workload, snapshot before
                workload_validations_before = self.db_cleanup_workload_validations(wid)
                snapshot_validations_before = self.db_cleanup_snapshot_validations(snapshot_id)

                restore_id = ""
                if (restore_test[1] == "selective"):
                    trilio_vol_snapshots_before = self.get_trilio_volume_snapshot(vol_snap_name)
                    # selective restore
                    rest_details = {}
                    rest_details['rest_type'] = 'selective'
                    rest_details['network_id'] = CONF.network.internal_network_id
                    rest_details['subnet_id'] = self.get_subnet_id(
                        CONF.network.internal_network_id)
                    rest_details['volume_type'] = volume_type_id
                    rest_details['instances'] = {vm_id: volumes}
                    payload = self.create_restore_json(rest_details)

                    # Trigger selective restore of full snapshot
                    restore_id = self.snapshot_selective_restore(
                        wid, snapshot_id,
                        restore_name="selective_restore_full_snap",
                        instance_details=payload['instance_details'],
                        network_details=payload['network_details'], restore_cleanup=True)
                    self.wait_for_snapshot_tobe_available(wid, snapshot_id)

                    if (self.getRestoreStatus(wid, snapshot_id, restore_id) == "available"):
                        reporting.add_test_step("Selective restore for instance with attached ceph", tvaultconf.PASS)
                    else:
                        raise Exception("Selective restore failed for instance with attached ceph")

                    restored_vms = self.get_restored_vm_list(restore_id)
                    LOG.debug("Restored vm(selective) ID : " + str(restored_vms))
                    restored_volumes = self.get_restored_volume_list(restore_id)
                    LOG.debug("Restored volumes list: {}".format(restored_volumes))
                    time.sleep(60)

                    # DB validations for restore before
                    restore_validations_before = self.db_cleanup_restore_validations(restore_id)
                    LOG.debug("db entries before deleting selective restore job: {}".format(restore_validations_before))

                    # Verify restored instance and volumes are deleted properly.
                    try:
                        self.delete_restored_vms(restored_vms, restored_volumes)
                        self.restore_delete(wid, snapshot_id, restore_id)
                        reporting.add_test_step("Deleted restored vms and volumes", tvaultconf.PASS)

                        # DB validations for selective restore after restore deletion
                        restore_validations_after_deletion = self.db_cleanup_restore_validations(restore_id)
                        if (all(value == 0 for value in restore_validations_after_deletion.values())):
                            reporting.add_test_step("selective: db cleanup validations post deleting restore job", tvaultconf.PASS)
                        else:
                            reporting.add_test_step("selective: db cleanup validations post deleting restore job", tvaultconf.FAIL)
                            reporting.set_test_script_status(tvaultconf.FAIL)
                    except Exception as e:
                        raise Exception(str(e))

                    # Delete workload snapshots and verify
                    self.snapshot_delete(wid, snapshot_id)
                    trilio_vol_snapshots_after = self.get_trilio_volume_snapshot(vol_snap_name)
                    if trilio_vol_snapshots_after == trilio_vol_snapshots_before:
                        LOG.debug("triliovault created snapshots are not deleted after deleting snapshots")
                    else:
                        raise Exception("triliovault created snapshots should not be deleted after deleting snapshots")

                    # DB validations for snapshots after deletion
                    snapshot_validations_after_deletion = self.db_cleanup_snapshot_validations(snapshot_id)
                    if (all(value == 0 for value in snapshot_validations_after_deletion.values())):
                        reporting.add_test_step("selective: db cleanup validations for snapshot ", tvaultconf.PASS)
                    else:
                        reporting.add_test_step("selective: db cleanup validations for snapshot ", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)

                    # Delete workloads and verify
                    self.workload_delete(wid)
                    time.sleep(30)
                    trilio_vol_snapshots_after = self.get_trilio_volume_snapshot(vol_snap_name)
                    if trilio_vol_snapshots_after != trilio_vol_snapshots_before:
                        LOG.debug("triliovault created snapshots are still present")
                        reporting.add_test_step("triliovault created snapshots are deleted after workload deletion",
                                                tvaultconf.PASS)
                    else:
                        raise Exception("triliovault created snapshots are NOT deleted after workload deletion")

                    # DB validations for workload after workload deletion
                    workload_validations_after_deletion = self.db_cleanup_workload_validations(wid)
                    if (all(value == 0 for value in workload_validations_after_deletion.values())):
                        reporting.add_test_step("selective: db cleanup validations for workload ", tvaultconf.PASS)
                    else:
                        reporting.add_test_step("selective: db cleanup validations for workload ", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)

                elif (restore_test[1] == "inplace"):
                    # Inplace restore for full snapshot
                    vol_snap_name_for_inplace = "TriliVault-Inplace_Snapshot"
                    trilio_vol_snapshots_before_restore = self.get_trilio_volume_snapshot(vol_snap_name)
                    LOG.debug("Volume snapshot details before inplace restore: {}".format(
                        trilio_vol_snapshots_before_restore))
                    rest_details = {}
                    rest_details['rest_type'] = 'inplace'
                    rest_details['volume_type'] = volume_type_id
                    rest_details['instances'] = {vm_id: volumes}
                    payload = self.create_restore_json(rest_details)

                    # Trigger inplace restore of full snapshot
                    restore_id = self.snapshot_inplace_restore(
                        wid, snapshot_id, payload, restore_cleanup=True)
                    self.wait_for_snapshot_tobe_available(wid, snapshot_id)
                    if (self.getRestoreStatus(wid, snapshot_id,
                                              restore_id) == "available"):
                        reporting.add_test_step("Inplace restore of full snapshot",
                                                tvaultconf.PASS)
                    else:
                        reporting.add_test_step("Inplace restore of full snapshot",
                                                tvaultconf.FAIL)
                    trilio_vol_snapshots_before = self.get_trilio_volume_snapshot(vol_snap_name_for_inplace)

                    # rbd cleanup verification for in_place restore
                    restored_vms = self.get_restored_vm_list(restore_id)
                    LOG.debug("Restored vm(in_place) ID : " + str(restored_vms))
                    restored_volumes = self.get_restored_volume_list(restore_id)
                    LOG.debug("Restored volumes list: {}".format(restored_volumes))
                    time.sleep(60)

                    # DB validations for restore before
                    restore_validations_before = self.db_cleanup_restore_validations(restore_id)
                    LOG.debug("db entries before deleting inplace restore job: {}".format(restore_validations_before))

                    self.restore_delete(wid, snapshot_id, restore_id)
                    # DB validations for in-place restore after restore cleanup
                    restore_validations_after_deletion = self.db_cleanup_restore_validations(restore_id)
                    if (all(value == 0 for value in restore_validations_after_deletion.values())):
                        reporting.add_test_step("inplace: db cleanup validations post deleting restore job", tvaultconf.PASS)
                    else:
                        reporting.add_test_step("inplace: db cleanup validations post deleting restore job", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)

                    # Delete workload snapshots and verify
                    self.snapshot_delete(wid, snapshot_id)
                    trilio_vol_snapshots_after = self.get_trilio_volume_snapshot(vol_snap_name_for_inplace)
                    if trilio_vol_snapshots_after:
                        LOG.debug(
                            "triliovault created snapshots for in_place restore are present after deleting workload snapshots")
                    else:
                        raise Exception(
                            "triliovault created snapshots for in_place restore are deleted after deleting workload snapshots")

                    # DB validations for snapshots after deletion
                    snapshot_validations_after_deletion = self.db_cleanup_snapshot_validations(snapshot_id)
                    if (all(value == 0 for value in snapshot_validations_after_deletion.values())):
                        reporting.add_test_step("inplace: db cleanup validations for snapshot ", tvaultconf.PASS)
                    else:
                        reporting.add_test_step("inplace: db cleanup validations for snapshot ", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)

                    # Delete workloads and verify
                    self.workload_delete(wid)
                    time.sleep(30)
                    # DB validations for workload after workload deletion
                    workload_validations_after_deletion = self.db_cleanup_workload_validations(wid)
                    if (all(value == 0 for value in workload_validations_after_deletion.values())):
                        reporting.add_test_step("inplace: db cleanup validations for workload ", tvaultconf.PASS)
                    else:
                        reporting.add_test_step("inplace: db cleanup validations for workload ", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)

                    trilio_vol_snapshots_after = self.get_trilio_volume_snapshot(vol_snap_name_for_inplace)
                    LOG.debug("Inplace restore - trilio_vol_snapshots_before : {}".format(trilio_vol_snapshots_before))
                    LOG.debug("Inplace restore - trilio_vol_snapshots_after : {}".format(trilio_vol_snapshots_after))

                    if trilio_vol_snapshots_after == trilio_vol_snapshots_before:
                        LOG.debug("triliovault created snapshots are still present")
                        reporting.add_test_step(
                            "triliovault created snapshots for in_place restore are present after workload deletion",
                            tvaultconf.PASS)
                    else:
                        raise Exception(
                            "triliovault created snapshots for in_place restore are deleted after workload deletion")

                    # Verify restored instance and volumes are deleted properly.
                    try:
                        self.delete_restored_vms(restored_vms, restored_volumes)
                        trilio_vol_snapshots_after = self.get_trilio_volume_snapshot(vol_snap_name_for_inplace)
                        if not trilio_vol_snapshots_after:
                            reporting.add_test_step(
                                "Deletion of vms, volumes and volume snapshots post inplace restore is successful",
                                tvaultconf.PASS)
                    except Exception as e:
                        raise Exception(str(e))

                elif (restore_test[1] == "oneclick"):
                    trilio_vol_snapshots_before = self.get_trilio_volume_snapshot(vol_snap_name)
                    self.delete_vm(vm_id)
                    time.sleep(10)
                    rest_details = {}
                    rest_details['rest_type'] = 'oneclick'
                    rest_details['volume_type'] = volume_type_id
                    payload = self.create_restore_json(rest_details)

                    # Trigger oneclick restore of full snapshot
                    restore_id = self.snapshot_inplace_restore(
                        wid, snapshot_id, payload, restore_cleanup=True)
                    self.wait_for_snapshot_tobe_available(wid, snapshot_id)
                    if (self.getRestoreStatus(wid, snapshot_id,
                                              restore_id) == "available"):
                        reporting.add_test_step("Oneclick restore of full snapshot",
                                                tvaultconf.PASS)
                    else:
                        reporting.add_test_step("Oneclick restore of full snapshot",
                                                tvaultconf.FAIL)

                    restored_vms = self.get_restored_vm_list(restore_id)
                    LOG.debug("Restored vm(selective) ID : " + str(restored_vms))
                    restored_volumes = self.get_restored_volume_list(restore_id)
                    LOG.debug("Restored volumes list: {}".format(restored_volumes))
                    time.sleep(60)

                    # DB validations for restore before
                    restore_validations_before = self.db_cleanup_restore_validations(restore_id)
                    LOG.debug("db entries before deleting oneclick restore job: {}".format(restore_validations_before))

                    self.restore_delete(wid, snapshot_id, restore_id)
                    # DB validations for oneclick restore after restore cleanup
                    restore_validations_after_deletion = self.db_cleanup_restore_validations(restore_id)
                    if (all(value == 0 for value in restore_validations_after_deletion.values())):
                        reporting.add_test_step("oneclick: db cleanup validations post deleting restore job", tvaultconf.PASS)
                    else:
                        reporting.add_test_step("oneclick: db cleanup validations post deleting restore job", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)

                    # Delete workload snapshots and verify
                    self.snapshot_delete(wid, snapshot_id)
                    trilio_vol_snapshots_after = self.get_trilio_volume_snapshot(vol_snap_name)
                    if trilio_vol_snapshots_after == trilio_vol_snapshots_before:
                        LOG.debug("triliovault created snapshots are not deleted after deleting snapshots")
                    else:
                        raise Exception("triliovault created snapshots should not be deleted after deleting snapshots")

                    # DB validations for snapshots after deletion
                    snapshot_validations_after_deletion = self.db_cleanup_snapshot_validations(snapshot_id)
                    if (all(value == 0 for value in snapshot_validations_after_deletion.values())):
                        reporting.add_test_step("oneclick: db cleanup validations for snapshot ", tvaultconf.PASS)
                    else:
                        reporting.add_test_step("oneclick: db cleanup validations for snapshot ", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)

                    # Delete workloads and verify
                    self.workload_delete(wid)
                    time.sleep(30)
                    # DB validations for workload after workload deletion
                    workload_validations_after_deletion = self.db_cleanup_workload_validations(wid)
                    if (all(value == 0 for value in workload_validations_after_deletion.values())):
                        reporting.add_test_step("oneclick: db cleanup validations for workload ", tvaultconf.PASS)
                    else:
                        reporting.add_test_step("oneclick: db cleanup validations for workload ", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)

                    trilio_vol_snapshots_after = self.get_trilio_volume_snapshot(vol_snap_name)
                    if trilio_vol_snapshots_after != trilio_vol_snapshots_before:
                        LOG.debug("triliovault created snapshots are still present")

                    try:
                        self.delete_restored_vms(restored_vms, restored_volumes)
                        reporting.add_test_step("Deleted restored vms and volumes", tvaultconf.PASS)
                    except Exception as e:
                        raise Exception(str(e))

                reporting.test_case_to_write()

            except Exception as e:
                LOG.error(f"Exception: {e}")
                reporting.add_test_step(str(e), tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                reporting.test_case_to_write()

    # Test case automated #OS-2031 for boot volume ceph/rbd/tripleo
    # http://192.168.15.51/testlink/linkto.php?tprojectPrefix=OS&item=testcase&id=OS-2031
    @decorators.attr(type='workloadmgr_api')
    def test_18_barbican(self):
        test_var = "tempest.api.workloadmgr.barbican.rbd_device_cleanup_.boot_ceph_volume_"
        restore_tests = [[test_var + "selectiverestore_api", "selective"], [test_var + "inplacerestore_api", "inplace"],
                         [test_var + "oneclickrestore_api", "oneclick"]]

        for restore_test in restore_tests:
            try:
                reporting.add_test_script(restore_test[0])
                try:
                    order_uuid = self.create_secret_order("sec_order1")
                    LOG.debug("Created secret order: {}".format(order_uuid))
                    time.sleep(10)
                    secret_uuid = self.get_secret_from_order(order_uuid)
                    LOG.debug("Getting secret key from secret order: {}".format(secret_uuid))
                    reporting.add_test_step("Creating secret key using secret order", tvaultconf.PASS)

                    # Get the details of luks-ceph (encrypted ceph) volumes from setup
                    volume_type_id = ""
                    for vol in CONF.volume.volume_types:
                        if (vol.lower().find("luks") != -1):
                            if (vol.lower().find("ceph") != -1) or (vol.lower().find("tripleo") != -1) or (
                                    vol.lower().find("rbd") != -1):
                                volume_type_id = CONF.volume.volume_types[vol]
                                LOG.debug("Encrypted volume for ceph/rbd found : {}".format(volume_type_id))
                            elif (vol.lower() == "luks"):
                                volume_type_id = CONF.volume.volume_types[vol]
                                LOG.debug("Encrypted volume for ceph/rbd found : {}".format(volume_type_id))

                    if not volume_type_id:
                        raise Exception("Exiting the test as encrypted ceph/rbd volume type is not found")

                    # Create bootable cinder volume using encrypted ceph/rbd volume
                    vol_count = 2
                    volumes = []
                    disk_names = ["vda", "vdb", "vdc"]
                    boot_volume_id = self.create_volume(
                        size=tvaultconf.bootfromvol_vol_size,
                        volume_type_id=volume_type_id,
                        image_id=CONF.compute.image_ref,
                        volume_cleanup=True)
                    self.set_volume_as_bootable(boot_volume_id)
                    LOG.debug(f"Bootable Volume ID : {boot_volume_id}")
                    block_mapping_details = [{"source_type": "volume",
                                              "delete_on_termination": "false",
                                              "boot_index": 0,
                                              "uuid": boot_volume_id,
                                              "destination_type": "volume"}]
                    vm_id = self.create_vm(
                        image_id="",
                        block_mapping_data=block_mapping_details,
                        vm_cleanup=True)

                    for i in range(vol_count):
                        volume_id = self.create_volume(
                            volume_type_id=volume_type_id)
                        volumes.append(volume_id)
                        self.attach_volume(volume_id, vm_id, attach_cleanup=True)
                    LOG.debug(f"Volumes attached: {volumes}")
                    reporting.add_test_step("Create instance with encrypted bootable ceph/rbd volume", tvaultconf.PASS)

                except Exception as e:
                    LOG.error(f"Exception: {e}")
                    raise Exception("prerequisite of instance with encrypted bootable ceph/rbd volume failed")
                self.mount_path = self.get_mountpoint_path()

                # Create workload with API
                wid = []
                try:
                    wid = self.workload_create([vm_id],
                                               encryption=True,
                                               secret_uuid=secret_uuid, workload_cleanup=True)
                    LOG.debug("Workload ID: " + str(wid))
                except Exception as e:
                    LOG.error(f"Exception: {e}")
                    raise Exception("Create encrypted workload with attached ceph volume")
                time.sleep(10)
                if (wid is not None):
                    self.wait_for_workload_tobe_available(wid)
                    self.workload_status = self.getWorkloadStatus(wid)
                    if (self.workload_status == "available"):
                        reporting.add_test_step("Created encrypted workload with attached ceph volume", tvaultconf.PASS)
                    else:
                        raise Exception("Create encrypted workload with attached ceph volume")
                else:
                    raise Exception("Create encrypted workload with attached ceph volume")

                snapshot_id = self.workload_snapshot(wid, True, snapshot_cleanup=True)
                self.wait_for_workload_tobe_available(wid)
                snapshot_status = self.getSnapshotStatus(wid, snapshot_id)
                if (snapshot_status == "available"):
                    reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                    snapshot_found = self.check_snapshot_exist_on_backend(
                        self.mount_path, wid, snapshot_id)
                    LOG.debug(f"snapshot_found: {snapshot_found}")
                    if snapshot_found:
                        reporting.add_test_step("Verify snapshot existence on " \
                                                "target backend", tvaultconf.PASS)
                        self._check_encryption_on_backend(wid, snapshot_id,
                                                          vm_id, disk_names, self.mount_path)
                    else:
                        raise Exception("Verify snapshot existence on target backend")
                else:
                    raise Exception("Create full snapshot")

                vol_snap_name = tvaultconf.triliovault_vol_snapshot_name
                restore_id = ""

                # selective restore
                if (restore_test[1] == "selective"):
                    trilio_vol_snapshots_before = self.get_trilio_volume_snapshot(vol_snap_name)
                    rest_details = {}
                    rest_details['rest_type'] = 'selective'
                    rest_details['network_id'] = CONF.network.internal_network_id
                    rest_details['subnet_id'] = self.get_subnet_id(
                        CONF.network.internal_network_id)
                    rest_details['volume_type'] = volume_type_id
                    rest_details['instances'] = {vm_id: volumes}
                    LOG.debug(rest_details)
                    payload = self.create_restore_json(rest_details)

                    # Trigger selective restore of full snapshot
                    restore_id = self.snapshot_selective_restore(
                        wid, snapshot_id,
                        restore_name="selective_restore_full_snap",
                        instance_details=payload['instance_details'],
                        network_details=payload['network_details'],
                        restore_cleanup=True)
                    self.wait_for_snapshot_tobe_available(wid, snapshot_id)

                    if (self.getRestoreStatus(wid, snapshot_id, restore_id) == "available"):
                        reporting.add_test_step("Selective restore for instance with bootable ceph", tvaultconf.PASS)
                    else:
                        raise Exception("Selective restore failed for instance with bootable ceph")

                    restored_vms = self.get_restored_vm_list(restore_id)
                    LOG.debug("Restored vm(selective) ID : " + str(restored_vms))
                    restored_volumes = self.get_restored_volume_list(restore_id)
                    LOG.debug("Restored volumes list: {}".format(restored_volumes))
                    time.sleep(60)

                    # Verify restored instance and volumes are deleted properly.
                    try:
                        self.delete_restored_vms(restored_vms, restored_volumes)
                        self.restore_delete(wid, snapshot_id, restore_id)
                        reporting.add_test_step("Deleted restored vms and volumes", tvaultconf.PASS)
                    except Exception as e:
                        raise Exception(str(e))

                    # Delete workload snapshots and verify
                    self.snapshot_delete(wid, snapshot_id)
                    trilio_vol_snapshots_after = self.get_trilio_volume_snapshot(vol_snap_name)
                    if trilio_vol_snapshots_after == trilio_vol_snapshots_before:
                        LOG.debug("triliovault created snapshots are not deleted after deleting snapshots")
                    else:
                        raise Exception("triliovault created snapshots should not be deleted after deleting snapshots")

                    # Delete workloads and verify
                    self.workload_delete(wid)
                    time.sleep(30)
                    trilio_vol_snapshots_after = self.get_trilio_volume_snapshot(vol_snap_name)
                    if trilio_vol_snapshots_after != trilio_vol_snapshots_before:
                        LOG.debug("triliovault created snapshots are still present")
                        reporting.add_test_step("triliovault created snapshots are deleted after workload deletion",
                                                tvaultconf.PASS)
                    else:
                        raise Exception("triliovault created snapshots are NOT deleted after workload deletion")


                elif (restore_test[1] == "inplace"):
                    # Inplace restore for full snapshot
                    vol_snap_name_for_inplace = "TriliVault-Inplace_Snapshot"
                    trilio_vol_snapshots_before_restore = self.get_trilio_volume_snapshot(vol_snap_name)
                    LOG.debug("Volume snapshot details before inplace restore: {}".format(
                        trilio_vol_snapshots_before_restore))
                    rest_details = {}
                    rest_details['rest_type'] = 'inplace'
                    rest_details['instances'] = {vm_id: volumes}
                    rest_details['volume_type'] = volume_type_id
                    payload = self.create_restore_json(rest_details)

                    # Trigger inplace restore of full snapshot
                    restore_id = self.snapshot_inplace_restore(
                        wid, snapshot_id, payload, restore_cleanup=True)
                    self.wait_for_snapshot_tobe_available(wid, snapshot_id)
                    if (self.getRestoreStatus(wid, snapshot_id,
                                              restore_id) == "available"):
                        reporting.add_test_step("Inplace restore of full snapshot",
                                                tvaultconf.PASS)
                    else:
                        reporting.add_test_step("Inplace restore of full snapshot",
                                                tvaultconf.FAIL)
                    trilio_vol_snapshots_before = self.get_trilio_volume_snapshot(vol_snap_name_for_inplace)

                    # rbd cleanup verification for in_place restore
                    restored_vms = self.get_restored_vm_list(restore_id)
                    LOG.debug("Restored vm(in_place) ID : " + str(restored_vms))
                    restored_volumes = self.get_restored_volume_list(restore_id)
                    LOG.debug("Restored volumes list: {}".format(restored_volumes))
                    time.sleep(60)

                    self.restore_delete(wid, snapshot_id, restore_id)

                    # Delete workload snapshots and verify
                    self.snapshot_delete(wid, snapshot_id)
                    trilio_vol_snapshots_after = self.get_trilio_volume_snapshot(vol_snap_name_for_inplace)
                    if trilio_vol_snapshots_after:
                        LOG.debug(
                            "triliovault created snapshots for in_place restore are present after deleting workload snapshots")
                    else:
                        raise Exception(
                            "triliovault created snapshots for in_place restore are deleted after deleting workload snapshots")

                    # Delete workloads and verify
                    self.workload_delete(wid)
                    time.sleep(30)
                    trilio_vol_snapshots_after = self.get_trilio_volume_snapshot(vol_snap_name_for_inplace)
                    LOG.debug("Inplace restore - trilio_vol_snapshots_before : {}".format(trilio_vol_snapshots_before))
                    LOG.debug("Inplace restore - trilio_vol_snapshots_after : {}".format(trilio_vol_snapshots_after))

                    if trilio_vol_snapshots_after == trilio_vol_snapshots_before:
                        LOG.debug("triliovault created snapshots are still present")
                        reporting.add_test_step(
                            "triliovault created snapshots for in_place restore are present after workload deletion",
                            tvaultconf.PASS)
                    else:
                        raise Exception(
                            "triliovault created snapshots for in_place restore are deleted after workload deletion")

                    # Verify restored instance and volumes are deleted properly.
                    try:
                        self.delete_restored_vms(restored_vms, restored_volumes)
                        trilio_vol_snapshots_after = self.get_trilio_volume_snapshot(vol_snap_name_for_inplace)
                        if not trilio_vol_snapshots_after:
                            reporting.add_test_step(
                                "Deletion of vms, volumes and volume snapshots post inplace restore is successful",
                                tvaultconf.PASS)
                    except Exception as e:
                        raise Exception(str(e))

                elif (restore_test[1] == "oneclick"):
                    trilio_vol_snapshots_before = self.get_trilio_volume_snapshot(vol_snap_name)
                    self.delete_vm(vm_id)
                    time.sleep(10)
                    rest_details = {}
                    rest_details['rest_type'] = 'oneclick'
                    rest_details['volume_type'] = volume_type_id
                    payload = self.create_restore_json(rest_details)

                    # Trigger oneclick restore of full snapshot
                    restore_id = self.snapshot_inplace_restore(
                        wid, snapshot_id, payload, restore_cleanup=True)
                    self.wait_for_snapshot_tobe_available(wid, snapshot_id)
                    if (self.getRestoreStatus(wid, snapshot_id,
                                              restore_id) == "available"):
                        reporting.add_test_step("Oneclick restore of full snapshot",
                                                tvaultconf.PASS)
                    else:
                        reporting.add_test_step("Oneclick restore of full snapshot",
                                                tvaultconf.FAIL)

                    restored_vms = self.get_restored_vm_list(restore_id)
                    LOG.debug("Restored vm(selective) ID : " + str(restored_vms))
                    restored_volumes = self.get_restored_volume_list(restore_id)
                    LOG.debug("Restored volumes list: {}".format(restored_volumes))
                    time.sleep(60)

                    # Delete workload snapshots and verify
                    self.snapshot_delete(wid, snapshot_id)
                    trilio_vol_snapshots_after = self.get_trilio_volume_snapshot(vol_snap_name)
                    if trilio_vol_snapshots_after == trilio_vol_snapshots_before:
                        LOG.debug("triliovault created snapshots are not deleted after deleting snapshots")
                    else:
                        raise Exception("triliovault created snapshots should not be deleted after deleting snapshots")

                    # Delete workloads and verify
                    self.workload_delete(wid)
                    time.sleep(30)
                    trilio_vol_snapshots_after = self.get_trilio_volume_snapshot(vol_snap_name)
                    if trilio_vol_snapshots_after != trilio_vol_snapshots_before:
                        LOG.debug("triliovault created snapshots are still present")

                    try:
                        self.delete_restored_vms(restored_vms, restored_volumes)
                        reporting.add_test_step("Deleted restored vms and volumes", tvaultconf.PASS)
                    except Exception as e:
                        raise Exception(str(e))

                reporting.test_case_to_write()

            except Exception as e:
                LOG.error(f"Exception: {e}")
                reporting.add_test_step(str(e), tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                reporting.test_case_to_write()


    # OS-2026
    # Test case automated #AUTO-53 for verification of secret key added to secret container.
    # http://192.168.15.51/testlink/linkto.php?tprojectPrefix=OS&item=testcase&id=OS-2026
    @decorators.attr(type='workloadmgr_api')
    def test_19_barbican(self):

        try:
            test_var = "tempest.api.workloadmgr.barbican.test_"
            tests = [[test_var + "create_secret_on_secret_container", 0],
                    [test_var  + "create_full_snapshot", 0],
                    [test_var  + "selective_restore", 0],
                    [test_var  + "inplace_restore", 0],
                    [test_var  + "oneclick_restore", 0]]


            reporting.add_test_script(tests[0][0])

            # create key pair...
            self.kp = self.create_key_pair(tvaultconf.key_pair_name)

            # create vm...
            self.vm_id = self.create_vm(key_pair=self.kp)

            # get floating ips
            fip = self.get_floating_ips()
            LOG.debug(f"Available floating ips are : {fip}")

            if len(fip) < 2:
                raise Exception("Floating ips unavailable")

            #assign ip and add data on it.
            self.set_floating_ip(fip[0], self.vm_id)

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.install_qemu(ssh)
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 3)
            md5sums_before_full = self._get_md5sum(ssh, ["/opt"])
            LOG.debug(f"md5sums_before_full: {md5sums_before_full}")
            ssh.close()

            #create secret
            self.secret_uuid = self.create_secret()

            #create secret container with secret_uuid.
            self.container_ref = self.create_secret_container(self.secret_uuid)

            if self.container_ref:
                reporting.add_test_step(
                    "Create secret container with an secret_href payload.",
                    tvaultconf.PASS)
                tests[0][1] = 1
            else:
                LOG.error("Create secret container with secret_href failed.")
                raise Exception("Create secret container with secret_href.")

            reporting.test_case_to_write()

            reporting.add_test_script(tests[1][0])
            # Create workload with CLI to pass secret uuid.
            workload_create_cmd = command_argument_string.workload_create_with_encryption + \
                                              " instance-id=" + str(self.vm_id) + \
                                              " --secret-uuid " + str(self.secret_uuid) + " --jobschedule enabled=False"

            error = cli_parser.cli_error(workload_create_cmd)
            if error and (str(error.strip('\n')).find('ERROR') != -1):
                LOG.error("Create workload Error: " + str(error))
                raise Exception("Create workload using secret uuid")
            else:
                LOG.debug("workload created successfully")


            time.sleep(10)
            # workload created successfully, we need to delete it. Get the workload id...
            self.wid = query_data.get_workload_id_in_creation(
                tvaultconf.workload_name)

            if(self.wid is not None):
                LOG.debug("Workload ID: " + str(self.wid))
                self.wait_for_workload_tobe_available(self.wid)
                self.workload_status = self.getWorkloadStatus(self.wid)
                if(self.workload_status == "available"):
                    LOG.debug("create workload with secret uuid passed.")
                    reporting.add_test_step("Create workload "\
                            "with secret uuid", tvaultconf.PASS)
                else:
                    LOG.error("create workload with secret uuid failed. Status is not available.")
                    raise Exception("Create workload with secret uuid")
            else:
                LOG.error("create workload with secret uuid failed. wid is not available.")
                raise Exception("Create workload with secret uuid")


            #create full snapshot...
            self.snapshot_id = self.workload_snapshot(self.wid, True)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id)
            if(self.snapshot_status == "available"):
                LOG.debug("Full snapshot created.")
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                tests[1][1] = 1
            else:
                LOG.error("Full snapshot creation failed.")
                raise Exception("Create full snapshot")


            reporting.test_case_to_write()

            #selective restore
            reporting.add_test_script(tests[2][0])
            rest_details = {}
            self.volumes = []
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
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[1])
                md5sums_after_full_selective = self._get_md5sum(ssh, ["/opt"])
                LOG.debug(f"md5sums_after_full_selective: {md5sums_after_full_selective}")
                ssh.close()

                if md5sums_before_full == \
                        md5sums_after_full_selective:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "File present on selective restored instance", tvaultconf.PASS)
                    tests[2][1] = 1
                else:
                    LOG.error("***MDSUMS DON'T MATCH***")
                    raise Exception("Selective restore of full snapshot - checksum failed.")
            else:
                LOG.error("Selective restore of full snapshot failed. Status not available.")
                raise Exception("Selective restore of full snapshot")


            reporting.test_case_to_write()

            #Inplace restore for full snapshot
            reporting.add_test_script(tests[3][0])
            rest_details = {}
            self.volumes = []
            rest_details['rest_type'] = 'inplace'
            rest_details['instances'] = {self.vm_id: self.volumes}
            payload = self.create_restore_json(rest_details)

            # Trigger inplace restore of full snapshot
            restore_id_2 = self.snapshot_inplace_restore(
                self.wid, self.snapshot_id, payload)

            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id)

            if(self.getRestoreStatus(self.wid, self.snapshot_id,
                    restore_id_2) == "available"):

                reporting.add_test_step("Inplace restore of full snapshot",
                        tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                time.sleep(5)
                md5sums_after_full_inplace = self._get_md5sum(ssh, ["/opt"])
                LOG.debug(f"md5sums_after_full_inplace: {md5sums_after_full_inplace}")
                ssh.close()

                if md5sums_before_full == \
                        md5sums_after_full_inplace:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "File present on inplace restored instance", tvaultconf.PASS)
                    tests[3][1] = 1
                else:
                    LOG.error("***MDSUMS DON'T MATCH***")
                    raise Exception("Inplace restore of full snapshot - checksum failed.")
            else:
                LOG.error("Inplace restore of full snapshot failed. Status not available.")
                raise Exception("Inplace restore of full snapshot")


            reporting.test_case_to_write()


            #oneclick restore
            reporting.add_test_script(tests[4][0])

            #delete original instance of vm.
            self.delete_vm(self.vm_id)

            time.sleep(10)
            rest_details = {}
            rest_details['rest_type'] = 'oneclick'
            payload = self.create_restore_json(rest_details)
            # Trigger oneclick restore of full snapshot
            restore_id_3 = self.snapshot_inplace_restore(
                self.wid, self.snapshot_id, payload)
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id)
            if(self.getRestoreStatus(self.wid, self.snapshot_id,
                    restore_id_3) == "available"):

                reporting.add_test_step("Oneclick restore of full snapshot",
                        tvaultconf.PASS)

                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                md5sums_after_full_oneclick = self._get_md5sum(ssh, ["/opt"])
                LOG.debug(f"md5sums_after_full_oneclick: {md5sums_after_full_oneclick}")
                ssh.close()

                if md5sums_before_full == \
                        md5sums_after_full_oneclick:
                    LOG.debug("***MDSUMS MATCH***")
                    reporting.add_test_step(
                        "File present on oneclick restored instance", tvaultconf.PASS)
                    tests[4][1] = 1
                else:
                    LOG.error("***MDSUMS DON'T MATCH***")
                    raise Exception("Oneclick restore of full snapshot - checksum failed")
            else:
                LOG.error("Oneclick restore of full snapshot failed. Status not available.")
                raise Exception("Oneclick restore of full snapshot")


            reporting.test_case_to_write()

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

    # End of test case OS-2026



