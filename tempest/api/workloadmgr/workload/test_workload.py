import os
import sys
import time
import datetime

from oslo_log import log as logging

from tempest import command_argument_string
from tempest import config
from tempest import reporting
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
    vm_id = None
    vol_id = None

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    @decorators.attr(type='workloadmgr_cli')
    def test_01_list_workloadtype(self):
        reporting.add_test_script(str(__name__) + "_list_workloadtype_cli")
        try:
            rc = cli_parser.cli_returncode(
                command_argument_string.workload_type_list)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-type-list command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-type-list command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            wc = query_data.get_available_workload_types()
            out = cli_parser.cli_output(
                command_argument_string.workload_type_list)
            if (int(wc) == int(out)):
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.PASS)
                LOG.debug(
                    "Workload type list command listed available workload types correctly")
            else:
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.FAIL)
                raise Exception(
                    "Workload type list command did not list available workload types correctly")
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_02_show_workloadtype(self):
        reporting.add_test_script(str(__name__) + "_show_workloadtype_cli")
        try:
            rc = cli_parser.cli_returncode(
                command_argument_string.workload_type_show)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-type-show command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-type-show command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            db_resp = query_data.get_workload_type_data(
                tvaultconf.workload_type_id)
            LOG.debug("Response from DB: " + str(db_resp))
            cmd_resp = cli_parser.cli_output(
                command_argument_string.workload_type_show)
            LOG.debug("Response from CLI: " + str(cmd_resp))

            if(db_resp[5] == tvaultconf.workload_type_id):
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.PASS)
                LOG.debug("Workload type response from CLI and DB match")
            else:
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.FAIL)
                raise Exception(
                    "Workload type response from CLI and DB do not match")
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_03_create_workload(self):
        reporting.add_test_script(str(__name__) + "_create_workload_cli")
        try:
            self.created = False
            self.vm_id = self.create_vm()
            self.volume_id = self.create_volume()
            self.attach_volume(self.volume_id, self.vm_id)

            # Create workload with CLI command
            workload_create = command_argument_string.workload_create + \
                " --instance instance-id=" + str(self.vm_id)
            rc = cli_parser.cli_returncode(workload_create)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-create command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-create command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            time.sleep(10)
            self.wid = query_data.get_workload_id_in_creation(tvaultconf.workload_name)
            LOG.debug("Workload ID: " + str(self.wid))
            if(self.wid is not None):
                self.wait_for_workload_tobe_available(self.wid)
                if(self.getWorkloadStatus(self.wid) == "available"):
                    reporting.add_test_step("Create workload", tvaultconf.PASS)
                else:
                    reporting.add_test_step("Create workload", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Create workload", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # DB validations for workload before
            workload_validations_before = self.db_cleanup_workload_validations(self.wid)
            LOG.debug("Workload table values before deletion: {}".format(workload_validations_before))

            # Delete workload
            self.workload_delete(self.wid)
            time.sleep(10)

            # DB validations for workload after workload cleanup
            workload_validations_after_deletion = self.db_cleanup_workload_validations(self.wid)
            if (all(value == 0 for value in workload_validations_after_deletion.values())):
                reporting.add_test_step("db cleanup validations for workload", tvaultconf.PASS)
            else:
                reporting.add_test_step("db cleanup validations for workload", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_04_create_workload(self):
        reporting.add_test_script(str(__name__) + "_create_workload_api")
        try:
            # Prerequisites
            self.created = False
            self.vm_id = self.create_vm()
            self.volume_id = self.create_volume()
            self.attach_volume(self.volume_id, self.vm_id)

            # Create workload with API
            self.wid = self.workload_create([self.vm_id])
            LOG.debug("Workload ID: " + str(self.wid))
            if(self.wid is not None):
                self.wait_for_workload_tobe_available(self.wid)
                if(self.getWorkloadStatus(self.wid) == "available"):
                    reporting.add_test_step("Create workload", tvaultconf.PASS)
                else:
                    reporting.add_test_step("Create workload", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                raise Exception("Create workload")
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_05_create_scheduled_workload(self):
        reporting.add_test_script(str(__name__) + "_create_scheduled_workload_cli")
        try:
            # Prerequisites
            self.created = False
            self.vm_id = self.create_vm()
            self.volume_id = self.create_volume()
            self.attach_volume(self.volume_id, self.vm_id)

            # Create workload with CLI command
            # Modify workload scheduler to enable and set the start date, time
            # and timezone
            now = datetime.datetime.utcnow()
            now_date = datetime.datetime.strftime(now, "%m/%d/%Y")
            now_time_plus_2 = now + datetime.timedelta(minutes=2)
            now_time_plus_2 = datetime.datetime.strftime(
                now_time_plus_2, "%I:%M %p")
            interval = tvaultconf.interval
            retention_policy_type = tvaultconf.retention_policy_type
            retention_policy_value = tvaultconf.retention_policy_value
            workload_create = command_argument_string.workload_create + " --instance instance-id=" + str(self.vm_id)\
                + " --jobschedule start_date=" + str(now_date.strip()) + " --jobschedule start_time='" + str(now_time_plus_2.strip())\
                + "' --jobschedule interval='" + str(interval) + "' --jobschedule retention_policy_type='"\
                + str(retention_policy_type) + "' --jobschedule retention_policy_value=" + str(retention_policy_value)\
                + " --jobschedule enabled=True"
            rc = cli_parser.cli_returncode(workload_create)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-create command with scheduler enabled",
                    tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-create command with scheduler enabled",
                    tvaultconf.PASS)
                LOG.debug("Command executed correctly")
            time.sleep(10)
            self.wid = query_data.get_workload_id_in_creation(tvaultconf.workload_name)
            LOG.debug("Workload ID: " + str(self.wid))
            self.wait_for_workload_tobe_available(self.wid)
            if(self.getWorkloadStatus(self.wid) == "available"):
                reporting.add_test_step(
                    "Create scheduled workload", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Create scheduled workload", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            self.schedule = self.getSchedulerStatus(self.wid)
            LOG.debug("Workload schedule: " + str(self.schedule))
            if(self.schedule):
                reporting.add_test_step("Verification", tvaultconf.PASS)
                LOG.debug("Workload schedule enabled")
            else:
                reporting.add_test_step("Verification", tvaultconf.FAIL)
                LOG.error("Workload schedule not enabled")

            # Cleanup
            # Delete workload
            self.workload_delete(self.wid)
            LOG.debug("Workload deleted successfully")
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_06_list_workload(self):
        reporting.add_test_script(str(__name__) + "_list_workload_cli")
        try:
            # Prerequisites
            self.created = False
            self.workload_instances = []
            self.vm_id = self.create_vm()
            self.volume_id = self.create_volume()
            self.attach_volume(self.volume_id, self.vm_id)

            # Create workload
            self.workload_instances.append(self.vm_id)
            self.wid = self.workload_create(
                self.workload_instances,
                workload_name=tvaultconf.workload_name)
            LOG.debug("Workload ID: " + str(self.wid))

            # List available workloads using CLI command
            rc = cli_parser.cli_returncode(
                command_argument_string.workload_list)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-list command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-list command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            wc = query_data.get_available_workloads(CONF.identity.tenant_id)
            out = cli_parser.cli_output(command_argument_string.workload_list)
            if (int(wc) == int(out)):
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.PASS)
                LOG.debug(
                    "Workload list command listed available workloads correctly")
            else:
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.FAIL)
                raise Exception(
                    "Workload list command did not list available workloads correctly, from db: " +
                    str(wc) + " , from cmd: " + str(out))
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_07_delete_workload(self):
        reporting.add_test_script(str(__name__) + "_delete_workload_cli")
        try:
            # Prerequisites
            self.deleted = False
            self.workload_instances = []
            self.vm_id = self.create_vm()
            self.volume_id = self.create_volume()
            self.attach_volume(self.volume_id, self.vm_id)

            # Create workload
            self.workload_instances.append(self.vm_id)
            self.wid = self.workload_create(
                self.workload_instances,
                workload_name=tvaultconf.workload_name,
                workload_cleanup=False)
            LOG.debug("Workload ID: " + str(self.wid))
            time.sleep(5)

            # Delete workload from CLI command
            rc = cli_parser.cli_returncode(
                command_argument_string.workload_delete + str(self.wid))
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-delete command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-delete command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            wc = query_data.get_deleted_workload(self.wid)
            LOG.debug("Workload status: " + str(wc))
            if(str(wc) == "deleted"):
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.PASS)
                LOG.debug("Workload successfully deleted")
                self.deleted = True
            else:
                retry_count = 0
                while (str(wc) != "deleted" or str(wc) != "None" or str(wc) != "error"):
                    time.sleep(15)
                    wc = query_data.get_deleted_workload(self.wid)
                    LOG.debug("Workload status: " + str(wc))
                    if (str(wc) == "None"):
                        reporting.add_test_step(
                            "Verification with DB", tvaultconf.PASS)
                        LOG.debug("Workload successfully deleted already. Returned None.")
                        self.deleted = True
                        break
                    elif (str(wc) == "deleted"):
                        LOG.error("Returned value deleted for workload deletion status. Not Expected return value.")
                        self.deleted = False
                        break
                    elif (str(wc) == "error"):
                        LOG.error("Returned value error for workload deletion status. Failed to delete Workload")
                        self.deleted = False
                        break
                    else:
                        if retry_count >= tvaultconf.max_retries:
                            LOG.error("Max retries to get workload delete status is over. Failed to delete workload.")
                            self.deleted = False
                            break
                        else:
                            LOG.debug("Retrying to delete workload again - retry count = "+ str(retry_count))
                            retry_count += 1
                #end of while loop.

            if (self.deleted == False):
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.FAIL)
                raise Exception("Workload did not get deleted")
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_08_show_workload(self):
        reporting.add_test_script(str(__name__) + "_show_workload_cli")
        try:
            # Prerequisites
            self.created = False
            self.workload_instances = []
            self.vm_id = self.create_vm(vm_name="bootfromvol_vm")
            self.volume_id = self.create_volume()
            self.attach_volume(self.volume_id, self.vm_id)

            # Create workload
            self.workload_instances.append(self.vm_id)
            self.wid = self.workload_create(
                self.workload_instances,
                workload_name=tvaultconf.workload_name)
            LOG.debug("Workload ID: " + str(self.wid))

            # Show workload details using CLI command
            rc = cli_parser.cli_returncode(
                command_argument_string.workload_show + self.wid)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-show command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-show command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            # Compare the workload details against database
            out = cli_parser.cli_output(
                command_argument_string.workload_show + self.wid)
            LOG.debug("Response from CLI: " + str(out))

            if(query_data.get_workload_display_name(self.wid) == cli_parser.cli_response_parser(out, 'name')):
                reporting.add_test_step(
                    "Verify workload name", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload name", tvaultconf.FAIL)
            if(query_data.get_workload_display_description(self.wid) == cli_parser.cli_response_parser(out, 'description')):
                reporting.add_test_step(
                    "Verify workload description", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload description", tvaultconf.FAIL)
            if(query_data.get_workload_status_by_id(self.wid) == cli_parser.cli_response_parser(out, 'status')):
                reporting.add_test_step(
                    "Verify workload status", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload status", tvaultconf.FAIL)

            instances_cli = []
            temp = eval(cli_parser.cli_response_parser(out, 'instances'))
            for i in range(0, len(temp)):
                instances_cli.append(temp[i]['id'])
            instances_cli.sort()
            instances_db = sorted(query_data.get_workload_vmids(self.wid))
            if(instances_db == instances_cli):
                reporting.add_test_step(
                    "Verify workload instances", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload instances", tvaultconf.FAIL)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_09_unlock_workload(self):
        reporting.add_test_script(str(__name__) + "_unlock_workload_cli")
        try:
            # Prerequisites
            self.created = False
            self.workload_instances = []
            self.vm_id = self.create_vm()
            self.volume_id = self.create_volume()
            self.attach_volume(self.volume_id, self.vm_id)
            self.workload_instances.append(self.vm_id)
            self.wid = self.workload_create(
                self.workload_instances,
                workload_name=tvaultconf.workload_name)
            LOG.debug("Workload ID: " + str(self.wid))
            time.sleep(5)

            # Create snapshot
            self.snapshot_id = self.workload_snapshot(
                self.wid, True, tvaultconf.snapshot_name)
            LOG.debug("Snapshot ID: " + str(self.snapshot_id))

            wc = query_data.get_workload_status_by_id(self.wid)
            LOG.debug("Workload status: " + str(wc))

            # Unlock workload using CLI command
            rc = cli_parser.cli_returncode(
                command_argument_string.workload_unlock + self.wid)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-unlock command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-unlock command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            # Get workload status
            wc = query_data.get_workload_status_by_id(self.wid)
            LOG.debug("Workload status: " + str(wc))

            if('available' == str(wc)):
                reporting.add_test_step("Verification", tvaultconf.PASS)
            else:
                raise Exception("Workload status update failed")

            try:
                self.wait_for_snapshot_tobe_available(
                    self.wid, self.snapshot_id)
                LOG.debug("Snapshot is available")
            except Exception as e:
                LOG.error("Snapshot is in error state")
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_10_workload_reset(self):
        reporting.add_test_script(str(__name__) + "_workload_reset_api")
        try:
            vm_id = self.create_vm(vm_cleanup=True)
            volume_id = self.create_volume(volume_cleanup=True)
            volumes = tvaultconf.volumes_parts
            self.attach_volume(volume_id, vm_id, attach_cleanup=True)
            time.sleep(40)
            i = 1
            workload_id = self.workload_create(
                [vm_id],
                workload_name="w1",
                workload_cleanup=True,
                description='test')
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

            self.created = False
            snapshot_id = self.workload_snapshot(
                workload_id, True, snapshot_name="Snap1", snapshot_cleanup=True)
            time.sleep(5)
            self.wait_for_workload_tobe_available(workload_id)
            if(self.getSnapshotStatus(workload_id, snapshot_id) == "available"):
                reporting.add_test_step(
                    "Create full snapshot-{}".format(i), tvaultconf.PASS)
                LOG.debug("Full snapshot available!!")
            else:
                reporting.add_test_step(
                    "Create full snapshot-{}".format(i), tvaultconf.FAIL)
                raise Exception("Snapshot creation failed")

            i += 1
            volsnaps_before = self.get_volume_snapshots(volume_id)
            LOG.debug("\nVolume snapshots after full snapshot : {}\n".format(
                volsnaps_before))
            self.workload_reset(workload_id)

            start_time = time.time()
            time.sleep(10)
            volsnaps_after = self.get_volume_snapshots(volume_id)
            while (len(volsnaps_after) != 0 and (time.time() - start_time < 600)):
                volsnaps_after = self.get_volume_snapshots(volume_id)
                time.sleep(5)
            if len(volsnaps_after) == 0:
                reporting.add_test_step("Temp Volume snapshot is deleted ", tvaultconf.PASS)
            else:
                LOG.debug("Workload reset failed")
                reporting.add_test_step("Temp Volume snapshot not deleted ", tvaultconf.FAIL)
                raise Exception("Workload reset failed as temp volume snapshot is not deleted")

            snapshot_id_1 = self.workload_snapshot(
                workload_id, True, snapshot_name="Snap2", snapshot_cleanup=True)

            time.sleep(5)
            self.wait_for_workload_tobe_available(workload_id)
            if(self.getSnapshotStatus(workload_id, snapshot_id_1) == "available"):
                reporting.add_test_step(
                    "Create full snapshot-{}".format(i), tvaultconf.PASS)
                LOG.debug("Full snapshot available!!")
            else:
                reporting.add_test_step(
                    "Create full snapshot-{}".format(i), tvaultconf.FAIL)
                raise Exception("Snapshot creation failed")

            isfull = self.getSnapshotDetails(workload_id, snapshot_id_1)[
                'snapshot_type']
            if isfull == "full":
                LOG.debug("Workload reset passed")
                reporting.add_test_step("Workload reset", tvaultconf.PASS)
                reporting.set_test_script_status(tvaultconf.PASS)
            else:
                raise Exception("Workload reset failed")
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_11_create_workload(self):
        reporting.add_test_script(str(__name__) + "_create_workload_api")
        try:
            self.created = False
            self.vm_id = self.create_vm()
            self.volume_id = self.create_volume()
            self.attach_volume(self.volume_id, self.vm_id)

            # Create workload
            self.wid = self.workload_create([self.vm_id])
            LOG.debug("Workload ID: " + str(self.wid))
            if(self.wid is not None):
                self.wait_for_workload_tobe_available(self.wid)
                if(self.getWorkloadStatus(self.wid) == "available"):
                    reporting.add_test_step("Create workload", tvaultconf.PASS)
                else:
                    reporting.add_test_step("Create workload", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Create workload", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_12_create_scheduled_workload(self):
        reporting.add_test_script(str(__name__) + "_create_scheduled_workload_api")
        try:
            # Prerequisites
            self.created = False
            self.vm_id = self.create_vm()
            self.volume_id = self.create_volume()
            self.attach_volume(self.volume_id, self.vm_id)

            # Create scheduled workload
            # Modify workload scheduler to enable and set the start date, time
            # and timezone
            now = datetime.datetime.utcnow()
            now_date = datetime.datetime.strftime(now, "%m/%d/%Y")
            now_time_plus_2 = now + datetime.timedelta(minutes=2)
            now_time_plus_2 = datetime.datetime.strftime(
                now_time_plus_2, "%I:%M %p")
            self.interval = tvaultconf.interval
            self.retention_policy_type = tvaultconf.retention_policy_type
            self.retention_policy_value = tvaultconf.retention_policy_value
            self.wid = self.workload_create([self.vm_id], 
                                    jobschedule={"start_date": now_date.strip(),
                                                 "start_time": now_time_plus_2.strip(),
                                                 "interval": self.interval,
                                                 "retention_policy_type":
                                                     self.retention_policy_type,
                                                 "retention_policy_value":
                                                     self.retention_policy_value,
                                                 "enabled": "True",
                                                 "workload_cleanup": "False"})
            LOG.debug("Workload ID: " + str(self.wid))
            self.wait_for_workload_tobe_available(self.wid)
            if(self.getWorkloadStatus(self.wid) == "available"):
                reporting.add_test_step(
                    "Create scheduled workload", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Create scheduled workload", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            self.schedule = self.getSchedulerStatus(self.wid)
            LOG.debug("Workload schedule: " + str(self.schedule))
            if(self.schedule):
                reporting.add_test_step("Verification for workload schedule", tvaultconf.PASS)
                LOG.debug("Workload schedule enabled")
            else:
                reporting.add_test_step("Verification for workload schedule", tvaultconf.FAIL)
                LOG.error("Workload schedule not enabled")

            # DB validations for workload before
            workload_validations_before = self.db_cleanup_workload_validations(self.wid)
            LOG.debug("Workload table values before deletion: {}".format(workload_validations_before))

            # Delete workload
            self.workload_delete(self.wid)
            time.sleep(10)

            # DB validations for workload after workload cleanup
            workload_validations_after_deletion = self.db_cleanup_workload_validations(self.wid)
            if (all(value == 0 for value in workload_validations_after_deletion.values())):
                reporting.add_test_step("db cleanup validations for scheduled workload", tvaultconf.PASS)
            else:
                reporting.add_test_step("db cleanup validations for scheduled workload", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_13_delete_workload(self):
        try:
            reporting.add_test_script(str(__name__) +\
                    "_delete_workload_db-only-true_cli")
            global vm_id
            global vol_id
            # Prerequisites
            self.vm_id = self.create_vm(vm_cleanup=False)
            self.volume_id = self.create_volume(volume_cleanup=False)
            self.attach_volume(self.volume_id, self.vm_id,
                    attach_cleanup=False)
            vm_id = self.vm_id
            vol_id = self.volume_id

            # Create workload
            self.wid = self.workload_create(
                [self.vm_id], workload_cleanup=False)
            LOG.debug("Workload ID: " + str(self.wid))
            time.sleep(5)

            self.snapshot_id = self.workload_snapshot(self.wid, True,
                    snapshot_cleanup=False)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id)
            if(self.snapshot_status == "available"):
                LOG.debug("Create full snapshot successful")
            else:
                raise Exception("Create full snapshot")

            self.mount_path = self.get_mountpoint_path()
            self.snapshot_found = self.check_snapshot_exist_on_backend(
                        self.mount_path, self.wid, self.snapshot_id)
            LOG.debug(f"snapshot_found: {self.snapshot_found}")
            if self.snapshot_found:
                reporting.add_test_step("Workload & snapshot exists"\
                        " on target backend", tvaultconf.PASS)
            else:
                raise Exception("Workload & snapshot does not exist"\
                        " on target backend")

            # Delete workload from CLI command
            cmd = command_argument_string.workload_delete_db + "True " +\
                    str(self.wid)
            rc = cli_parser.cli_returncode(cmd)
            if rc != 0:
                raise Exception(
                    "Execute workload-delete command with database_only True")
            else:
                reporting.add_test_step(
                    "Execute workload-delete command with database_only True",
                    tvaultconf.PASS)

            time.sleep(5)
            wc = query_data.get_deleted_workload(self.wid)
            LOG.debug("Workload status: " + str(wc))
            if wc:
                raise Exception("Workload not deleted from DB")
            else:
                reporting.add_test_step(
                    "Workload deleted from DB", tvaultconf.PASS)

            self.snapshot_found = self.check_snapshot_exist_on_backend(
                        self.mount_path, self.wid, self.snapshot_id)
            LOG.debug(f"snapshot_found: {self.snapshot_found}")
            if self.snapshot_found:
                reporting.add_test_step("Workload & snapshot exists"\
                        " on target backend", tvaultconf.PASS)
            else:
                reporting.add_test_step("Workload & snapshot does not exist"\
                        " on target backend", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_14_delete_workload(self):
        try:
            reporting.add_test_script(str(__name__) +\
                    "_delete_workload_db-only-false_cli")
            global vm_id
            global vol_id
            self.vm_id = vm_id
            self.volume_id = vol_id

            # Create workload
            self.wid = self.workload_create(
                [self.vm_id], workload_cleanup=False)
            LOG.debug("Workload ID: " + str(self.wid))
            time.sleep(5)

            self.mount_path = self.get_mountpoint_path()
            self.workload_found = self.check_workload_exist_on_backend(
                        self.mount_path, self.wid)
            LOG.debug(f"workload_found: {self.workload_found}")
            if self.workload_found:
                reporting.add_test_step("Workload exists"\
                        " on target backend", tvaultconf.PASS)
            else:
                raise Exception("Workload does not exist on target backend")

            # Delete workload from CLI command
            cmd = command_argument_string.workload_delete_db + "False " +\
                    str(self.wid)
            rc = cli_parser.cli_returncode(cmd)
            if rc != 0:
                raise Exception(
                    "Execute workload-delete command with database_only False")
            else:
                reporting.add_test_step(
                    "Execute workload-delete command with database_only False",
                    tvaultconf.PASS)

            time.sleep(5)
            wc = query_data.get_deleted_workload(self.wid)
            LOG.debug("Workload status: " + str(wc))
            if wc:
                raise Exception("Workload not deleted from DB")
            else:
                reporting.add_test_step(
                    "Workload deleted from DB", tvaultconf.PASS)

            self.workload_found = self.check_workload_exist_on_backend(
                        self.mount_path, self.wid)
            LOG.debug(f"workload_found: {self.workload_found}")
            if self.workload_found:
                reporting.add_test_step("Workload exists"\
                        " on target backend", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Workload does not exist"\
                        " on target backend", tvaultconf.PASS)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()
            #Cleanup instance and volume
            self.delete_vm(self.vm_id)
            self.delete_volume(self.volume_id)

    @decorators.attr(type='workloadmgr_api')
    def test_15_workload_get_orphaned_workloads_list(self):
        try:

            reporting.add_test_script(
                str(__name__) + "_workload_get_orphaned_workloads_list")

            vm_id = self.create_vm()
            LOG.debug("\nVm id : {}\n".format(str(vm_id)))

            # create a temp user1.
            user_details1 = self.createUser()

            if user_details1 == False:
                LOG.error("Failed to create user.")
                raise Exception("Failed to create user.")

            self.temp_user_id_1 = user_details1['id']
            self.temp_user_name_1 = user_details1['name']

            # create temp project1.
            project_details_1 = self.create_project()
            LOG.debug("Project created details - {}".format(project_details_1["name"]))
            self.temp_tenant_id_1 = project_details_1["id"]
            self.temp_tenant_name_1 = project_details_1["name"]

            # assign trustee role
            role_id = self.get_role_id(tvaultconf.trustee_role)
            if len(role_id) != 1:
                raise Exception("Role ID not returned")

            # assign role to user1 and current project1.
            if self.assign_role_to_user_project(self.temp_tenant_id_1,
                                                self.temp_user_id_1, role_id[0], False):
                LOG.debug("Role assigned to user1 and project1")
                reporting.add_test_step("Role assignment to user1 and project1", tvaultconf.PASS)
            else:
                raise Exception("Role assignment to user1 and project1 failed")

            os.environ['OS_USERNAME'] = CONF.identity.backupuser
            os.environ['OS_PASSWORD'] = CONF.identity.backupuser_password

            ### create workload ###
            workload_create = command_argument_string.workload_create + " --instance instance-id=" + str(vm_id)
            rc = cli_parser.cli_returncode(workload_create)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-create command",
                    tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-create command",
                    tvaultconf.PASS)
                LOG.debug("Command executed correctly")
            time.sleep(10)
            self.wid = query_data.get_workload_id_in_creation(tvaultconf.workload_name)
            LOG.debug("Workload ID: " + str(self.wid))
            self.wait_for_workload_tobe_available(self.wid)
            if (self.getWorkloadStatus(self.wid) == "available"):
                reporting.add_test_step(
                    "Create workload", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Create workload", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # use temp user and temp project for workload reassign.
            rc = self.workload_reassign(self.temp_tenant_id_1, self.wid, self.temp_user_id_1)
            if rc == 0:
                LOG.debug(
                    f"Workload reassign to temp user1 {self.temp_user_name_1} with temp tenant1 {self.temp_tenant_name_1} is passed")
                reporting.add_test_step(
                    "Workload reassign to temp user1 {} with temp project1 {}".format(self.temp_user_name_1,
                                                                                      self.temp_tenant_name_1),
                    tvaultconf.PASS)
            else:
                LOG.error(
                    f"Workload reassign to temp user1 {self.temp_user_name_1} with temp tenant1 {self.temp_tenant_name_1} is failed")
                raise Exception(
                    "Workload reassign to temp user1 {} with temp tenant1 {}".format(self.temp_user_name_1,
                                                                                     self.temp_tenant_name_1))

            os.environ['OS_PROJECT_NAME'] = CONF.identity.project_alt_name
            os.environ['OS_PROJECT_ID'] = CONF.identity.tenant_id_1
            os.environ['OS_USERNAME'] = CONF.identity.username
            os.environ['OS_PASSWORD'] = CONF.identity.password

            # List available workloads using CLI command
            rc = cli_parser.cli_returncode(
                command_argument_string.workload_get_orphaned_workloads_list)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload_get_orphaned_workloads_list command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload_get_orphaned_workloads_list command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            out = cli_parser.cli_output(command_argument_string.workload_get_orphaned_workloads_list)
            if (tvaultconf.workload_name in str(out)):
                reporting.add_test_step(
                    "Verification with workload name", tvaultconf.PASS)
                LOG.debug(
                    "workload_get_orphaned_workloads_list command listed available workloads correctly")
            else:
                reporting.add_test_step(
                    "Verification with workload name", tvaultconf.FAIL)
                raise Exception(
                    "workload_get_orphaned_workloads_list command did not list available workloads correctly from cmd: " + str(out))

            os.environ['OS_PROJECT_NAME'] = CONF.identity.project_name
            os.environ['OS_PROJECT_ID'] = CONF.identity.tenant_id

            # delete the current created user.
            resp = self.deleteUser(self.temp_user_id_1)
            if resp:
                LOG.debug(f"temp User1 {self.temp_user_name_1} deleted successfully")
                reporting.add_test_step(
                    "temp User1 {} deletion".format(self.temp_user_name_1), tvaultconf.PASS)

            else:
                LOG.error(f"temp User1 {self.temp_user_name_1} is not deleted successfully")
                raise Exception("temp User1 {} deletion".format(self.temp_user_name_1))

            # delete the current created project.
            resp = self.delete_project(self.temp_tenant_id_1)
            if resp:
                LOG.debug(f"temp Project1 {self.temp_tenant_name_1} deleted successfully")
                reporting.add_test_step(
                    "temp Project1 {} deletion".format(self.temp_tenant_name_1), tvaultconf.PASS)
            else:
                LOG.error(f"temp Project1 {self.temp_tenant_name_1} is not deleted successfully")
                raise Exception("temp Project1 {} deletion".format(self.temp_tenant_name_1))

            # Cleanup
            # Delete workload
            self.workload_delete(self.wid)
            LOG.debug("Workload deleted successfully")
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()
