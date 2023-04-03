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
    def test_01_snapshot_deletion(self):
        try:
            reporting.add_test_script(str(__name__) + "_delete_full_backup_from_backup_chain")
            self.kp = self.create_key_pair(tvaultconf.key_pair_name)
            self.vm_id = self.create_vm(key_pair=self.kp)
            LOG.debug("VM ID : " + str(self.vm_id))
            self.volumes = []
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
                    reporting.add_test_step("Create workload",
                                            tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Create workload",
                                        tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("Workload creation failed")

            self.snapshots = []
            full_snapshot_sizes = []
            incr_snapshot_sizes = []
            for i in range(0, (rpv + 1)):
                if i == 0:
                    is_full = True
                    snapshot_type = "full"
                else:
                    is_full = False
                    snapshot_type = "incremental"
                    ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
                    self.addCustomfilesOnLinuxVM(ssh, "/opt", 5)
                    md5sums_before_incr = self._get_md5sum(ssh, ["/opt"])
                    LOG.debug(f"md5sums_before_incr: {md5sums_before_incr}")
                    ssh.close()
                snapshot_id = self.workload_snapshot(
                    workload_id, is_full, snapshot_cleanup=False)
                self.snapshots.append(snapshot_id)
                self.wait_for_workload_tobe_available(workload_id)
                if (self.getSnapshotStatus(workload_id, snapshot_id) == "available"):
                    reporting.add_test_step(
                        "Create " + snapshot_type + " snapshot-{}".format(i + 1), tvaultconf.PASS)
                    LOG.debug(snapshot_type + " snapshot available!!")
                    self.snapshot_found = self.check_snapshot_exist_on_backend(
                        self.mount_path, workload_id, snapshot_id)
                    LOG.debug(f"snapshot_found: {self.snapshot_found}")
                    if self.snapshot_found:
                        reporting.add_test_step("Verify snapshot existence on " \
                                                "target backend", tvaultconf.PASS)
                        for disk_name in self.disk_names:
                            snapshot_size = int(
                                self.check_snapshot_size_on_backend(self.mount_path, workload_id, snapshot_id,
                                                                    self.vm_id, disk_name))
                            LOG.debug(f"{snapshot_type} snapshot_size for {disk_name}: {snapshot_size} MB")
                            if i == 0:
                                full_snapshot_sizes.append({disk_name: snapshot_size})
                                LOG.debug(f"Full snapshot sizes for all disks: {full_snapshot_sizes}")
                            else:
                                incr_snapshot_sizes.append({disk_name: snapshot_size})
                                LOG.debug(f"Incremental snapshot sizes for all disks: {incr_snapshot_sizes}")
                    else:
                        raise Exception("Verify snapshot existence on target backend")
                else:
                    reporting.add_test_step(
                        "Create " + snapshot_type + " snapshot-{}".format(i + 1), tvaultconf.FAIL)
                    raise Exception(snapshot_type + " snapshot creation failed")

            snapshotlist = self.getSnapshotList(workload_id=workload_id)
            LOG.debug(f"Snapshots created in test: {self.snapshots}, " \
                      f"Snapshots returned in snapshot_list: {snapshotlist}")
            if len(snapshotlist) == rpv:
                reporting.add_test_step("Retention", tvaultconf.PASS)
                LOG.debug("Retention worked!!")
            else:
                reporting.add_test_step("Retention", tvaultconf.FAIL)
                LOG.debug("Retention didn't work!!")
                raise Exception("Retention failed")

            # Check first snapshot is deleted or not after retention value
            # exceed
            deleted_snapshot_id = self.snapshots[0]
            LOG.debug("snapshot id of first snapshot is : " +
                      str(deleted_snapshot_id))
            if deleted_snapshot_id in snapshotlist:
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
                self.mount_path, workload_id, deleted_snapshot_id)
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

            # DB validations for snapshots after cleanup
            snapshot_validations_after_deletion = self.db_cleanup_snapshot_validations(deleted_snapshot_id)

            # For full snapshot, new entry is added in table "vm_recent_snapshot". For incr, same entry is updated.
            # However, when we delete incr snapshot, this entry is removed.
            # vm_recent_snapshot table has FK with Snapshot having ondelete="CASCADE" effect,
            # so whenever the snapshot is deleted it's respective entry from this table would get removed.
            LOG.debug("Print values for {}".format(snapshot_validations_after_deletion))

            if (all(value == 0 for value in snapshot_validations_after_deletion.values())):
                reporting.add_test_step("db cleanup validations for full snapshot", tvaultconf.PASS)
            else:
                reporting.add_test_step("db cleanup validations for full snapshot", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            for snapshot in snapshotlist:
                # Mount incremental snapshot
                mount_status = self.mount_snapshot(
                    workload_id, snapshot, self.frm_id, mount_cleanup=False)
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

                unmount_status = self.unmount_snapshot(workload_id, snapshot)
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
                filecount_in_snapshots = {
                    snapshot: 1}
                search_path = "/opt/File_4"
                self._filesearch(self.vm_id, filecount_in_snapshots, search_path)

            # Check first snapshot is deleted from backup target when retention
            # value exceed
            is_backup_chain_exist = self.check_backup_chain_by_quemu_cmd(
                self.mount_path, workload_id, snapshot_id, self.vm_id)
            LOG.debug("Backup chain for snapshot : %s" % is_backup_chain_exist)
            if not is_backup_chain_exist:
                LOG.debug("Backup chain for snapshot is deleted from backup target")
                reporting.add_test_step(
                    "Backup chain for snapshot deleted from backup target",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Backup chain for snapshot deleted from backup target",
                    tvaultconf.FAIL)

            if (tvaultconf.cleanup):
                for snapshot in snapshotlist:
                    self.addCleanup(self.snapshot_delete,
                                    workload_id, snapshot)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()
