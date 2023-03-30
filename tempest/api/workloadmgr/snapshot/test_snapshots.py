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

            workload_id = self.wid
            vm_id = self.vm_id
            volume_id = self.volume_id

            LOG.debug("workload is:" + str(workload_id))
            LOG.debug("vm id: " + str(vm_id))
            LOG.debug("volume id: " + str(volume_id))

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
            global full_snapshot_size
            mount_path = self.get_mountpoint_path()
            wc = self.wait_for_snapshot_tobe_available(
                workload_id, snapshot_id)
            if (str(wc) == "available"):
                reporting.add_test_step("Full snapshot", tvaultconf.PASS)
                LOG.debug("Workload snapshot successfully completed")
                self.created = True
                full_snapshot_size = self.check_snapshot_size_on_backend(mount_path, workload_id,
                                                                         snapshot_id, vm_id)
                LOG.debug(f"full snapshot_size for vda: {full_snapshot_size} MB")
            else:
                if (str(wc) == "error"):
                    pass
            if (self.created == False):
                reporting.add_test_step("Full snapshot", tvaultconf.FAIL)
                raise Exception("Workload snapshot did not get created")

            # DB validations for full snapshots before
            full_snapshot_validations = self.db_cleanup_snapshot_validations(snapshot_id)
            LOG.debug("db entries after triggering full snapshot: {}".format(full_snapshot_validations))
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
            global full_snapshot_size
            incr_snapshot_size = 0
            self.created = False
            LOG.debug("workload is:" + str(workload_id))
            LOG.debug("vm id: " + str(vm_id))

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
            mount_path = self.get_mountpoint_path()
            if (str(wc) == "available"):
                reporting.add_test_step(
                    "Incremental snapshot", tvaultconf.PASS)
                LOG.debug("Workload incremental snapshot successfully completed")
                self.created = True
                # Verification for disk size for full and incr
                incr_snapshot_size = self.check_snapshot_size_on_backend(mount_path, workload_id,
                                                                         self.incr_snapshot_id, vm_id)
                LOG.debug(f"incr snapshot_size for vda: {incr_snapshot_size} MB")
                if int(full_snapshot_size) > int(incr_snapshot_size):
                    reporting.add_test_step(f"Full snapshot size is greater than incr snapshot size for vda",
                                            tvaultconf.PASS)
                else:
                    reporting.add_test_step(f"Full snapshot size is greater than incr snapshot size for vda",
                                            tvaultconf.FAIL)
            if (self.created == False):
                reporting.add_test_step(
                    "Incremental snapshot", tvaultconf.FAIL)
                raise Exception(
                    "Workload incremental snapshot did not get created")

            # DB validations for incr snapshots before
            incr_snapshot_validations_before = self.db_cleanup_snapshot_validations(self.incr_snapshot_id)
            LOG.debug("db entries after triggering incr snapshot: {}".format(incr_snapshot_validations_before))

            # Cleanup : # Delete snapshot
            self.snapshot_delete(workload_id, self.incr_snapshot_id)
            LOG.debug("Incremental Snapshot deleted successfully")

            # DB validations for snapshots after cleanup
            snapshot_validations_after_deletion = self.db_cleanup_snapshot_validations(self.incr_snapshot_id)

            # For full snapshot, new entry is added in table "vm_recent_snapshot". For incr, same entry is updated.
            # However, when we delete incr snapshot, this entry is removed.
            # vm_recent_snapshot table has FK with Snapshot having ondelete="CASCADE" effect,
            # so whenever the snapshot is deleted it's respective entry from this table would get removed.
            LOG.debug("Print values for {}".format(snapshot_validations_after_deletion))

            if (all(value == 0 for value in snapshot_validations_after_deletion.values())):
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

    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    @decorators.attr(type='workloadmgr_cli')
    def test_4_cancel_snapshot(self):
        try:
            reporting.add_test_script(str(__name__) + "_cancel_snapshot_cli_with_invalid_options")

            global workload_id
            LOG.debug("workload is:" + str(workload_id))

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

            # Snapshot cancel CLI with invalid options
            snapshot_cancel_novalue = command_argument_string.snapshot_cancel
            err_msg1 = tvaultconf.error_cancel_snapshot_cli_without_any_options
            error1 = cli_parser.cli_error(snapshot_cancel_novalue)
            if error1 and (str(error1.strip('\n')).find(err_msg1) != -1):
                LOG.debug("Snapshot cancel cli with no snapshot id returned correct error " + str(error1))
                reporting.add_test_step("Snapshot cancel cli with no option returned correct error",
                                        tvaultconf.PASS)
            else:
                LOG.debug("Snapshot cancel cli with no snapshot id returned no error")
                reporting.add_test_step("Snapshot cancel cli with no snapshot id returned correct error",
                                        tvaultconf.FAIL)

            # Snapshot cancel CLI with invalid options
            snapshot_cancel_invalid = command_argument_string.snapshot_cancel + "invalid"
            err_msg2 = tvaultconf.error_cancel_snapshot_cli_with_invalid_workloadid_option
            error2 = cli_parser.cli_error(snapshot_cancel_invalid)
            if error2 and (str(error2.strip('\n')).find(err_msg2) != -1):
                LOG.debug("Snapshot cancel cli with invalid snapshot id returned correct error " + str(error2))
                reporting.add_test_step("Snapshot cancel cli with invalid option returned correct error",
                                        tvaultconf.PASS)
            else:
                LOG.debug("Snapshot cancel cli with invalid snapshot id returned no error")
                reporting.add_test_step("Snapshot cancel cli with invalid snapshot id returned correct error",
                                        tvaultconf.FAIL)

            reporting.test_case_to_write()

            reporting.add_test_script(str(__name__) + "_cancel_snapshot_cli")

            snapshot_cancel = command_argument_string.snapshot_cancel + snapshot_id
            LOG.debug("Cancel snapshot command: " + str(snapshot_cancel))
            rc1 = cli_parser.cli_returncode(snapshot_cancel)
            if rc1 != 0:
                reporting.add_test_step(
                    "Execute snapshot-cancel command",
                    tvaultconf.FAIL)
                raise Exception("snapshot-cancel Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute snapshot-cancel command",
                    tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            self.wait_for_workload_tobe_available(workload_id)
            snapshot_status = self.getSnapshotStatus(workload_id,
                                                          snapshot_id)
            if (snapshot_status == "cancelled"):
                reporting.add_test_step("Full snapshot cancelled", tvaultconf.PASS)
                LOG.debug("Workload snapshot successfully cancelled")
            else:
                reporting.add_test_step("Full snapshot not cancelled", tvaultconf.FAIL)
                raise Exception("Workload snapshot did not get cancelled")


            # Cleanup : # Delete snapshot
            self.snapshot_delete(workload_id, snapshot_id)
            LOG.debug("Incremental Snapshot deleted successfully")

            # DB validations for snapshots after cleanup
            snapshot_validations_after_deletion = self.db_cleanup_snapshot_validations(snapshot_id)

            # DB validations for full snapshots before
            full_snapshot_validations = self.db_cleanup_snapshot_validations(snapshot_id)
            LOG.debug("db entries after triggering full snapshot: {}".format(full_snapshot_validations))
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    @decorators.attr(type='workloadmgr_cli')
    def test_5_delete_snapshot(self):
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
            snapshot_validations_after_deletion = self.db_cleanup_snapshot_validations(snapshot_id)
            if (all(value == 0 for value in snapshot_validations_after_deletion.values())):
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
            time.sleep(10)

            # DB validations for workload after workload cleanup
            workload_validations_after_deletion = self.db_cleanup_workload_validations(workload_id)
            if (all(value == 0 for value in workload_validations_after_deletion.values())):
                reporting.add_test_step("db cleanup validations for workload", tvaultconf.PASS)
            else:
                reporting.add_test_step("db cleanup validations for workload", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # Delete vm
            self.delete_vm(vm_id)

            # Delete volume
            self.delete_volume(volume_id)

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
