import json
import datetime
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

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.install_qemu(ssh)
            self.addCustomfilesOnLinuxVM(ssh, "/test1", 2)
            ssh.close()

            self.mount_path = self.get_mountpoint_path()
            now = datetime.datetime.utcnow()
            now_date = datetime.datetime.strftime(now, "%m/%d/%Y")
            now_time_plus_12 = now + datetime.timedelta(minutes=12)
            now_time_plus_12 = datetime.datetime.strftime(
                now_time_plus_12, "%I:%M %p")

            self.schedule = {"start_date": now_date.strip(),
                             "start_time": now_time_plus_12.strip(),
                             "hourly": tvaultconf.hourly_scheduler,
                             "manual": tvaultconf.manual_retention,
                             "enabled": "False"}
            rpv = int(self.schedule['manual']['retention'])
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
            for i in range(0, rpv):
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

            # Check full snapshot is not deleted from backup target
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

            backing_chain = self.get_backing_chain(self.mount_path,
                    workload_id, self.snapshots[-1], self.vm_id)
            LOG.debug(f"Backing chain for last incremental snapshot is {backing_chain}")

            backing_chain_intact = False
            if backing_chain.find('No such file or directory') != -1:
                LOG.error("Backing chain does not exist")
                raise Exception("Verify backing chain")

            backing_chain = json.loads(backing_chain)
            for bc in backing_chain:
                if bc['filename'].find(self.snapshots[-1]) != -1:
                    backing_chain_intact = True
                    break
            LOG.debug(f"backing_chain_intact: {backing_chain_intact}")

            if backing_chain_intact:
                reporting.add_test_step("Verify backing chain", tvaultconf.PASS)
            else:
                raise Exception("Verify backing chain")

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
                reporting.add_test_step("Create new snapshot",
                        tvaultconf.PASS)
            else:
                raise Exception("Create new snapshot")
            if backend:
                reporting.add_test_step("Verify snapshot existence on "\
                         " target backend", tvaultconf.PASS)
            else:
                raise Exception("Verify snapshot existence on target backend")

            # Check first snapshot is deleted from backup target
            is_snapshot_exist = self.check_snapshot_exist_on_backend(
                self.mount_path, workload_id, self.snapshots[0])
            LOG.debug("Snapshot exist : %s" % is_snapshot_exist)
            if not is_snapshot_exist:
                LOG.debug("Full snapshot is deleted from backup target")
                reporting.add_test_step(
                    "Full snapshot is deleted from backup target",
                    tvaultconf.PASS)
            else:
                raise Exception(
                    "Full snapshot is not deleted from backup target")

            # DB validations for full snapshot after cleanup
            snapshot_validations_after_deletion = \
                    self.db_cleanup_snapshot_validations(self.snapshots[0])

            LOG.debug("Print values for {}".format(
                    snapshot_validations_after_deletion))
            if snapshot_validations_after_deletion['snapshots'] == 0:
                reporting.add_test_step("Full snapshot is deleted from DB",
                        tvaultconf.PASS)
            else:
                raise Exception("Full snapshot is not deleted from DB")

            # File search
            filecount_in_snapshots = {new_snap_id: 1}
            search_path = "/test1/File_2"
            self._filesearch(self.vm_id, filecount_in_snapshots, search_path)

            new_snap_data = self.getSnapshotDetails(workload_id, new_snap_id)
            if new_snap_data['snapshot_type'].lower() == 'full':
                reporting.add_test_step("New snapshot chain created",
                        tvaultconf.PASS)
            else:
                raise Exception("New snapshot chain not created")

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

