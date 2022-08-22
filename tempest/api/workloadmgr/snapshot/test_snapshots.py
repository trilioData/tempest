import os
import sys
import time

from oslo_log import log as logging

from tempest import command_argument_string
from tempest import config
from tempest import reporting
from tempest import test
from tempest import tvaultconf
from tempest.api.workloadmgr import base
from tempest.lib import decorators
from tempest.util import cli_parser
from tempest.util import query_data

sys.path.append(os.getcwd())

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']
    workload_id = None
    snapshot_id = None
    vm_id = None
    volume_id = None

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    @test.pre_req({'type': 'basic_workload'})
    @decorators.attr(type='smoke')
    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    @decorators.attr(type='workloadmgr_cli')
    def test_1_create_full_snapshot(self):
        try:
            reporting.add_test_script(str(__name__) + "_create_full_snapshot")
            if self.exception != "":
                LOG.debug("pre req failed")
                reporting.add_test_step(str(self.exception), tvaultconf.FAIL)
                raise Exception(str(self.exception))
            LOG.debug("pre req completed")

            global vm_id
            global volume_id
            global workload_id
            global snapshot_id
            global full_snapshot_validations_before

            workload_id = self.wid
            vm_id = self.vm_id
            volume_id = self.volume_id

            LOG.debug("workload is:" + str(workload_id))
            LOG.debug("vm id: " + str(vm_id))
            LOG.debug("volume id: " + str(volume_id))
            
            # DB validations for incr snapshots before 
            full_snapshot_validations_before = self.db_cleanup_snapshot_validations()
            
            self.created = False

            # Create snapshot with CLI command
            create_snapshot = command_argument_string.snapshot_create + workload_id
            LOG.debug("Create snapshot command: " + str(create_snapshot))
            rc = cli_parser.cli_returncode(create_snapshot)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-snapshot command with --full",
                    tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-snapshot command with --full",
                    tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            time.sleep(5)
            snapshot_id = query_data.get_inprogress_snapshot_id(workload_id)
            LOG.debug("Snapshot ID: " + str(snapshot_id))

            wc = self.wait_for_snapshot_tobe_available(
                workload_id, snapshot_id)
            if (str(wc) == "available"):
                reporting.add_test_step("Full snapshot", tvaultconf.PASS)
                LOG.debug("Workload snapshot successfully completed")
                self.created = True
            else:
                if (str(wc) == "error"):
                    pass
            if (self.created == False):
                reporting.add_test_step("Full snapshot", tvaultconf.FAIL)
                raise Exception("Workload snapshot did not get created")

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    @decorators.attr(type='workloadmgr_cli')
    def test_2_create_incremental_snapshot(self):
        try:
            reporting.add_test_script(
                str(__name__) + "_create_incremental_snapshot")

            global workload_id
            self.created = False
            LOG.debug("workload is:" + str(workload_id))
            
            # DB validations for incr snapshots before 
            snapshot_validations_before = self.db_cleanup_snapshot_validations()
            
            # Create incremental snapshot using CLI command
            create_snapshot = command_argument_string.incr_snapshot_create + workload_id
            LOG.debug("Create snapshot command: " + str(create_snapshot))
            rc = cli_parser.cli_returncode(create_snapshot)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-snapshot command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-snapshot command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            time.sleep(5)
            self.incr_snapshot_id = query_data.get_inprogress_snapshot_id(
                workload_id)
            LOG.debug("Incremental Snapshot ID: " + str(self.incr_snapshot_id))

            # Wait for incremental snapshot to complete
            wc = self.wait_for_snapshot_tobe_available(
                workload_id, self.incr_snapshot_id)
            if (str(wc) == "available"):
                reporting.add_test_step(
                    "Incremental snapshot", tvaultconf.PASS)
                LOG.debug("Workload incremental snapshot successfully completed")
                self.created = True
            if (self.created == False):
                reporting.add_test_step(
                    "Incremental snapshot", tvaultconf.FAIL)
                raise Exception(
                    "Workload incremental snapshot did not get created")
            
            # Cleanup : # Delete snapshot
            self.snapshot_delete(workload_id, self.incr_snapshot_id)
            LOG.debug("Incremental Snapshot deleted successfully")
            
            # DB validations for snapshots after cleanup
            snapshot_validations_after_deletion = self.db_cleanup_snapshot_validations()
            
            # For full snapshot, new entry is added in table "vm_recent_snapshot". For incr, same entry is updated. 
            # However, when we delete incr snapshot, this entry is removed.
            # vm_recent_snapshot table has FK with Snapshot having ondelete="CASCADE" effect,
            # so whenever the snapshot is deleted it's respective entry from this table would get removed. 
            # Below code change would prevent test failure, as it is expected behavior.
            snapshot_validations_after_deletion['vm_recent_snapshot'] += 1
            LOG.debug("Print values for {}".format(snapshot_validations_after_deletion))
            
            if (snapshot_validations_after_deletion == snapshot_validations_before):
                reporting.add_test_step("db cleanup validations for incr snapshot", tvaultconf.PASS)
            else:
                reporting.add_test_step("db cleanup validations for incr snapshot", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    @decorators.attr(type='workloadmgr_cli')
    def test_3_list_snapshot(self):
        try:
            reporting.add_test_script(str(__name__) + "_list_snapshot")

            # List snapshots using CLI command
            rc = cli_parser.cli_returncode(
                command_argument_string.snapshot_list)
            if rc != 0:
                reporting.add_test_step(
                    "Execute snapshot-list command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute snapshot-list command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            wc = query_data.get_available_snapshots(CONF.identity.tenant_id)
            out = cli_parser.cli_output(command_argument_string.snapshot_list)
            if(int(wc) == int(out)):
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.PASS)
                LOG.debug(
                    "Snapshot list command listed available snapshots correctly")
            else:
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.FAIL)
                raise Exception(
                    "Snapshot list command did not list available snapshots correctly")

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    @decorators.attr(type='workloadmgr_cli')
    def test_4_delete_snapshot(self):
        try:
            global workload_id
            global snapshot_id
            global volume_id
            global vm_id

            reporting.add_test_script(str(__name__) + "_delete_snapshot")

            # Delete snapshot using CLI command
            rc = cli_parser.cli_returncode(
                command_argument_string.snapshot_delete + snapshot_id)
            if rc != 0:
                reporting.add_test_step(
                    "Execute snapshot-delete command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute snapshot-delete command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")
            start_time = time.time()
            time.sleep(5)
            wc = 0
            while (str(wc) == "0" and (time.time() - start_time < 600)):
                wc = query_data.get_workload_snapshot_delete_status(
                    tvaultconf.snapshot_name, tvaultconf.snapshot_type_full, snapshot_id)
                LOG.debug("Snapshot Delete status: " + str(wc))
                time.sleep(5)
            if(str(wc) == "None"):
                LOG.debug("Snapshot is already deleted. Returned return value as None.")
                reporting.add_test_step("Verification", tvaultconf.PASS)
            elif(str(wc) == "1"):
                LOG.error("Unexpected return value as 1 while checking snapshot delete status")
                reporting.add_test_step("Verification", tvaultconf.FAIL)
                raise Exception("Snapshot did not get deleted")
            else:
                LOG.error("Timeout Waiting for snapshot deletion for the workload.")
                reporting.add_test_step("Verification", tvaultconf.FAIL)
                raise Exception("Snapshot did not get deleted")
            
            time.sleep(10)
            # DB validations for snapshots after cleanup
            snapshot_validations_after_deletion = self.db_cleanup_snapshot_validations()
            #snapshot_validations_after_deletion["vm_recent_snapshot"] -= 1
            if (snapshot_validations_after_deletion == full_snapshot_validations_before):
                reporting.add_test_step("db cleanup validations for full snapshot", tvaultconf.PASS)
            else:
                reporting.add_test_step("db cleanup validations for full snapshot", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            
            # Cleanup
            # Delete volume
            self.volume_snapshots = self.get_available_volume_snapshots()
            self.delete_volume_snapshots(self.volume_snapshots)
            
            # Delete workload
            self.workload_delete(workload_id)

            # Delete vm
            self.delete_vm(vm_id)

            # Delete volume
            self.delete_volume(volume_id)
    
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
