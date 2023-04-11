import json
from tempest.api.workloadmgr import base
from tempest import config
from tempest.lib import decorators
from oslo_log import log as logging
from tempest import tvaultconf
from tempest import reporting

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

    def _create_snapshot(self, workload_id, is_full, snapshot_cleanup):
        snapshot_id = self.workload_snapshot(workload_id, is_full,
                snapshot_cleanup=snapshot_cleanup)
        self.wait_for_workload_tobe_available(workload_id)
        return snapshot_id

    def _verify_snapshot(self, workload_id, snapshot_id, snapshot_type):
        if (self.getSnapshotStatus(workload_id, snapshot_id) == "available"):
            LOG.debug(snapshot_type + " snapshot available!!")
            self.snapshot_found = self.check_snapshot_exist_on_backend(
                    self.mount_path, workload_id, snapshot_id)
            LOG.debug(f"snapshot_found: {self.snapshot_found}")
            if self.snapshot_found:
                for disk_name in self.disk_names:
                    snapshot_size = int(self.check_snapshot_size_on_backend(
                        self.mount_path, workload_id, snapshot_id, self.vm_id,
                        disk_name))
                    LOG.debug(f"{snapshot_type} snapshot_size for "\
                            f"{disk_name}: {snapshot_size} MB")
                    if snapshot_type.lower() == 'full':
                        self.full_snapshot_sizes.append({disk_name: snapshot_size})
                        LOG.debug(f"Full snapshot sizes for all disks: {self.full_snapshot_sizes}")
                    else:
                        self.incr_snapshot_sizes.append({disk_name: snapshot_size})
                        LOG.debug(f"Incremental snapshot sizes for all disks: {self.incr_snapshot_sizes}")
                return True, True
            else:
                return True, False
        else:
            return False, False

    def _filesearch(self, vm_id, filecount_in_snapshots, search_path):
        filesearch_id = self.filepath_search(vm_id, search_path)
        filesearch_status = self.getSearchStatus(filesearch_id)
        if filesearch_status == 'error':
            reporting.add_test_step("File search failed", tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        else:
            snapshot_wise_filecount = self.verifyFilepath_Search(
                filesearch_id, search_path)
            LOG.debug(f"snapshot_wise_filecount: {snapshot_wise_filecount}")

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

    @decorators.attr(type='workloadmgr_api')
    def test_01_snapshot_deletion(self):
        try:
            reporting.add_test_script(str(__name__) + "_full_snapshot_from_backup_chain")
            self.kp = self.create_key_pair(tvaultconf.key_pair_name)
            self.vm_id = self.create_vm(key_pair=self.kp)
            LOG.debug("VM ID : " + str(self.vm_id))
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
            self.addCustomfilesOnLinuxVM(ssh, "/test1", 2)
            ssh.close()

            self.mount_path = self.get_mountpoint_path()

            retention = int(tvaultconf.retention_policy_value)
            self.schedule = {
                "fullbackup_interval": "1",
                "enabled": False,
                "retention_policy_type": tvaultconf.retention_policy_type,
                "retention_policy_value": retention}
            rpv = int(self.schedule['retention_policy_value'])
            workload_id = self.workload_create(
                [self.vm_id],
                jobschedule=self.schedule,
                workload_cleanup=True)
            LOG.debug("Workload ID: " + str(workload_id))
            if (workload_id is not None):
                self.wait_for_workload_tobe_available(workload_id)
                if (self.getWorkloadStatus(workload_id) == "available"):
                    reporting.add_test_step("Create workload",
                                            tvaultconf.PASS)
                else:
                    raise Exception("Create workload")

            else:
                raise Exception("Workload creation failed")

            self.snapshots = []
            self.full_snapshot_sizes = []
            self.incr_snapshot_sizes = []
            for i in range(0, rpv-1):
                if i == 0:
                    is_full = True
                    snapshot_type = "full"
                    snapshot_cleanup = False
                else:
                    is_full = False
                    snapshot_type = "incremental"
                    snapshot_cleanup = True
                    ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                    self.addCustomfilesOnLinuxVM(ssh, "/test2", 2)
                    ssh.close()

                snapshot_id = self._create_snapshot(
                    workload_id, is_full, snapshot_cleanup)
                self.snapshots.append(snapshot_id)
                snap, backend = self._verify_snapshot(workload_id,
                        snapshot_id, snapshot_type)
                if snap:
                    reporting.add_test_step("Create " + snapshot_type + \
                        " snapshot-{}".format(i + 1), tvaultconf.PASS)
                else:
                    raise Exception("Create " + snapshot_type + \
                        " snapshot-{}".format(i + 1))
                if backend:
                    reporting.add_test_step("Verify snapshot existence on "\
                            " target backend", tvaultconf.PASS)
                else:
                    raise Exception("Verify snapshot existence on target backend")

            if self.snapshot_delete(workload_id, self.snapshots[0]):
                LOG.debug("Full snapshot deleted successfully")
                reporting.add_test_step("Delete full snapshot", tvaultconf.PASS)
            else:
                raise Exception("Delete full snapshot")

            snapshotlist = self.getSnapshotList(workload_id=workload_id)
            LOG.debug(f"Snapshots created in test: {self.snapshots}, " \
                      f"Snapshots returned in snapshot_list: {snapshotlist}")

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.addCustomfilesOnLinuxVM(ssh, "/test3", 2)
            ssh.close()
            new_snap_id = self._create_snapshot(
                    workload_id, False, True)
            self.snapshots.append(new_snap_id)
            snap, backend = self._verify_snapshot(workload_id,
                        new_snap_id, snapshot_type)
            if snap:
                reporting.add_test_step("Create incremental snapshot",
                        tvaultconf.PASS)
            else:
                raise Exception("Create incremental snapshot")
            if backend:
                reporting.add_test_step("Verify snapshot existence on "\
                         " target backend", tvaultconf.PASS)
            else:
                raise Exception("Verify snapshot existence on target backend")

            # Check first snapshot is not deleted from backup target
            is_snapshot_exist = self.check_snapshot_exist_on_backend(
                self.mount_path, workload_id, self.snapshots[0])
            LOG.debug("Snapshot exist : %s" % is_snapshot_exist)
            if is_snapshot_exist:
                LOG.debug("Full snapshot is not deleted from backup target")
                reporting.add_test_step(
                    "Full snapshot is not deleted from backup target",
                    tvaultconf.PASS)
            else:
                raise Exception(
                    "Full snapshot is deleted from backup target")

            # DB validations for full snapshot after cleanup
            snapshot_validations_after_deletion = \
                    self.db_cleanup_snapshot_validations(self.snapshots[0])

            # For full snapshot, new entry is added in table
            # "vm_recent_snapshot". For incr, same entry is updated. However,
            # when we delete incr snapshot, this entry is removed.
            # vm_recent_snapshot table has FK with Snapshot having
            # ondelete="CASCADE" effect, so whenever the snapshot is deleted
            # it's respective entry from this table would get removed.
            LOG.debug("Print values for {}".format(
                    snapshot_validations_after_deletion))
            if snapshot_validations_after_deletion['snapshots'] == 1:
                reporting.add_test_step("Full snapshot exists in DB",
                        tvaultconf.PASS)
            else:
                raise Exception("Full snapshot deleted from DB")

            '''
            if (all(value == 0 for value in
                    snapshot_validations_after_deletion.values())):
                reporting.add_test_step("db cleanup validations for full "\
                        "snapshot", tvaultconf.PASS)
            else:
                reporting.add_test_step("db cleanup validations for full "\
                        "snapshot", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            '''

            # Mount latest incremental snapshot
            mount_status = self.mount_snapshot(
                    workload_id, new_snap_id, self.frm_id, mount_cleanup=False)
            if mount_status:
                reporting.add_test_step("Snapshot mount of incremental snapshot",
                        tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        fip[1], self.frm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh,
                        file_name="File_2").decode('UTF-8').split('\n')
                LOG.debug(f"output_list: {output_list}")
                ssh.close()
                flag = 0
                for i in output_list:
                    if 'vda1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that mountpoint mounted is shown on FVM instance",
                            tvaultconf.PASS)
                        flag = 1
                        if '/test1/File_2' in i:
                            reporting.add_test_step(
                                "Verification of file's existance on mounted snapshot",
                                tvaultconf.PASS)
                        else:
                            reporting.add_test_step(
                                "Verification of file's existance on mounted snapshot",
                                tvaultconf.FAIL)
                            reporting.set_test_script_status(tvaultconf.FAIL)

                if flag == 0:
                    reporting.add_test_step(
                        "Verify that mountpoint mounted is shown on FVM instance",
                        tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Snapshot mount of incremental snapshot", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            unmount_status = self.unmount_snapshot(workload_id, new_snap_id)
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

            # File search
            filecount_in_snapshots = {new_snap_id: 1}
            search_path = "/test1/File_2"
            self._filesearch(self.vm_id, filecount_in_snapshots, search_path)

            backing_chain = self.get_backing_chain(self.mount_path, 
                    workload_id, new_snap_id, self.vm_id)
            LOG.debug(f"Backing chain for snapshot {new_snap_id} is {backing_chain}")

            backing_chain_intact = False
            if backing_chain.find('No such file or directory') != -1:
                LOG.error("Backing chain does not exist")
                raise Exception("Verify backing chain")

            backing_chain = json.loads(backing_chain)
            for bc in backing_chain:
                if bc['filename'].find(self.snapshots[0]) != -1:
                    backing_chain_intact = True
                    break
            LOG.debug(f"backing_chain_intact: {backing_chain_intact}")

            if backing_chain_intact:
                reporting.add_test_step("Verify backing chain", tvaultconf.PASS)
            else:
                raise Exception("Verify backing chain")

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

