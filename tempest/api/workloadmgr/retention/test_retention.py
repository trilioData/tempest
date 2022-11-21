from tempest import reporting
import os
import sys

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
        reporting.add_test_script(str(__name__))

    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    @decorators.attr(type='workloadmgr_api')
    def test_retention(self):
        try:
            vm_id = self.create_vm(vm_cleanup=True)
            LOG.debug("VM ID : " + str(vm_id))
            i = 1

            jobschedule = {
                'retention_policy_type': 'Number of Snapshots to Keep',
                'retention_policy_value': '3',
                'full_backup_interval': '2',
                'enabled': false}
            rpv = int(jobschedule['retention_policy_value'])
            workload_id = self.workload_create(
                [vm_id],
                tvaultconf.parallel,
                jobschedule=jobschedule,
                workload_cleanup=True)
            LOG.debug("Workload ID: " + str(workload_id))
            if(workload_id is not None):
                self.wait_for_workload_tobe_available(workload_id)
                if(self.getWorkloadStatus(workload_id) == "available"):
                    reporting.add_test_step("Create workload", tvaultconf.PASS)
                else:
                    reporting.add_test_step("Create workload", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Create workload", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("Workload creation failed")

            snapshot_ids = []
            for i in range(0, (rpv + 1)):
                snapshot_id = self.workload_snapshot(
                    workload_id, True, snapshot_cleanup=False)
                self.wait_for_workload_tobe_available(workload_id)
                if(self.getSnapshotStatus(workload_id, snapshot_id) == "available"):
                    snapshot_ids.append(snapshot_id)
                    reporting.add_test_step(
                        "Create full snapshot-{}".format(i + 1), tvaultconf.PASS)
                    LOG.debug("Full snapshot available!!")
                else:
                    reporting.add_test_step(
                        "Create full snapshot-{}".format(i + 1), tvaultconf.FAIL)
                    raise Exception("Snapshot creation failed")

            snapshotlist = self.getSnapshotList(workload_id=workload_id)
            if len(snapshotlist) == rpv:
                reporting.add_test_step("Retention", tvaultconf.PASS)
                LOG.debug("Retention worked!!")
            else:
                reporting.add_test_step("Retention", tvaultconf.FAIL)
                LOG.debug("Retention didn't work!!")
                raise Exception("Retention failed")

            snapshot_id1 = snapshot_ids[0]
            self.mount_path = self.get_mountpoint_path()
            self.snapshot_found = self.check_snapshot_exist_on_backend(self.mount_path, workload_id, snapshot_id1)
            LOG.debug(f"snapshot_found: {self.snapshot_found}")
            if not self.snapshot_found:
                reporting.add_test_step("Retention verified on backup target, snapshot is deleted",
                                        tvaultconf.PASS)
            else:
                LOG.debug("Retention failed")
                reporting.add_test_step("Retention falied on backup target, snapshot is not deleted",
                                        tvaultconf.FAIL)
                raise Exception("Retention failed")
            if (tvaultconf.cleanup):
                for snapshot in snapshotlist:
                    self.addCleanup(self.snapshot_delete,
                                    workload_id, snapshot)

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
