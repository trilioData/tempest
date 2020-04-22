import time
import datetime
from tempest.util import query_data
from tempest.util import cli_parser
from tempest import command_argument_string
from tempest import reporting
from tempest import tvaultconf
from oslo_log import log as logging
from tempest import test
from tempest import config
from tempest.api.workloadmgr import base
import sys
import os
sys.path.append(os.getcwd())

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
        reporting.add_test_script(str(__name__))

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_1_modify_workload_tvault1045_add_instance(self):
        reporting.add_test_script(str(__name__) + "_tvault1045_add_instance")
        try:
            # Prerequisites
            self.created = False
            self.workload_instances = []

            # Launch instance
            self.vm_id = self.create_vm()
            LOG.debug("VM ID: " + str(self.vm_id))

            # Create volume
            self.volume_id = self.create_volume()
            LOG.debug("Volume ID: " + str(self.volume_id))

            # Attach volume to the instance
            self.attach_volume(self.volume_id, self.vm_id)
            LOG.debug("Volume attached")

            # Create workload with scheduler enabled
            self.workload_instances.append(self.vm_id)
            self.wid = self.workload_create(
                self.workload_instances, tvaultconf.parallel, workload_name=tvaultconf.workload_name, workload_cleanup=True)
            LOG.debug("Workload ID: " + str(self.wid))

            # Launch second instance
            self.vm_id2 = self.create_vm()
            LOG.debug("VM ID2: " + str(self.vm_id2))

            # Create volume
            self.volume_id2 = self.create_volume()
            LOG.debug("Volume ID2: " + str(self.volume_id2))

            # Attach volume to the instance
            self.attach_volume(self.volume_id2, self.vm_id2)
            LOG.debug("Volume2 attached")

            # Modify workload to add new instance using CLI command
            workload_modify_command = command_argument_string.workload_modify + "--instance instance-id=" + \
                str(self.vm_id2) + " --instance instance-id=" + \
                str(self.vm_id) + " " + str(self.wid)
            rc = cli_parser.cli_returncode(workload_modify_command)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-modify command to add one more vm", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-modify command to add one more vm", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            self.wait_for_workload_tobe_available(self.wid)
            workload_vm_count = query_data.get_available_vms_of_workload(
                self.wid)
            if (workload_vm_count == 2):
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.PASS)
                LOG.debug("Vm has been added successfully")
            else:
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.FAIL)
                raise Exception("Vm has not been added")

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_2_modify_workload_scheduler_disable(self):
        reporting.add_test_script(str(__name__) + "_scheduler_disable")
        try:
            # Prerequisites
            self.created = False
            self.workload_instances = []

            # Launch instance
            self.vm_id = self.create_vm()
            LOG.debug("VM ID-2: " + str(self.vm_id))

            # Create volume
            self.volume_id = self.create_volume()
            LOG.debug("Volume ID-2: " + str(self.volume_id))

            # Attach volume to the instance
            self.attach_volume(self.volume_id, self.vm_id)
            LOG.debug("Volume attached-2")

            # Create workload with scheduler enabled
            self.workload_instances.append(self.vm_id)
            self.wid = self.workload_create(
                self.workload_instances, tvaultconf.parallel, workload_name=tvaultconf.workload_name, workload_cleanup=True)
            LOG.debug("Workload ID-2: " + str(self.wid))

            # Verify workload created with scheduler enable
            status = self.getSchedulerStatus(self.wid)
            if status:
                reporting.add_test_step(
                    "Workload created with scheduler enabled", tvaultconf.PASS)
                LOG.debug("Workload created with scheduler enabled successfully")
            else:
                reporting.add_test_step(
                    "Workload created with scheduler enabled", tvaultconf.FAIL)
                raise Exception(
                    "Workload has not been created with scheduler enabled")

            # Get workload scheduler details
            schedule_details = self.getSchedulerDetails(self.wid)
            scheduled_start_time = schedule_details['start_time']
            interval = schedule_details['interval']

            # Change global job scheduler to disable
            LOG.debug("Change Global job scheduler to disable")
            status = self.disable_global_job_scheduler()
            if not status:
                reporting.add_test_step(
                    "Global job scheduler disable", tvaultconf.PASS)
                LOG.debug("Global job scheduler disabled successfully")
            else:
                reporting.add_test_step(
                    "Global job scheduler disable", tvaultconf.FAIL)
                raise Exception("Global job scheduler not disabled")

            # Modify workload scheduler to disable
            workload_modify_command = command_argument_string.workload_modify + \
                str(self.wid) + " --jobschedule enabled=False"
            error = cli_parser.cli_error(workload_modify_command)
            if error and (str(error.strip('\n')).find("Cannot update scheduler related fields when global jobscheduler is disabled.") != -1):
                reporting.add_test_step(
                    "Does not execute workload-modify scheduler disable", tvaultconf.PASS)
                LOG.debug("Command executed correctly")
                reporting.add_test_step(
                    "Throws proper message", tvaultconf.PASS)
                LOG.debug("Error message :" + str(error))
            else:
                reporting.add_test_step(
                    "Does not execute workload-modify scheduler disable", tvaultconf.FAIL)
                reporting.add_test_step(
                    "Throws proper message", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")

            # Change global job scheduler to enable
            LOG.debug("Change Global job scheduler to enable")
            status = self.enable_global_job_scheduler()
            if status:
                reporting.add_test_step(
                    "Global job scheduler enable", tvaultconf.PASS)
                LOG.debug("Global job scheduler enabled successfully")
            else:
                reporting.add_test_step(
                    "Global job scheduler enable", tvaultconf.FAIL)
                raise Exception("Global job scheduler not enabled")

            # Modify workload scheduler to disable using CLI command
            workload_modify_command = command_argument_string.workload_modify + \
                str(self.wid) + " --jobschedule enabled=False"
            rc = cli_parser.cli_returncode(workload_modify_command)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-modify scheduler disable", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-modify scheduler disable", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            # Verify workload scheduler changed to disable
            status = self.getSchedulerStatus(self.wid)
            if status:
                reporting.add_test_step(
                    "Verify workload scheduler disabled", tvaultconf.FAIL)
                LOG.debug("workload scheduler disabled unsuccessfully")
            else:
                reporting.add_test_step(
                    "Verify workload scheduler disabled", tvaultconf.PASS)
                LOG.debug("workload scheduler disabled successfully")

            # Verify interval value and nest_snapshot_run values
            schedule_details = self.getSchedulerDetails(self.wid)
            interval_after_disable = schedule_details['interval']

            if interval == interval_after_disable and 'nextrun' not in schedule_details:
                reporting.add_test_step(
                    "Verify Interval and Next snapshot run time values are correct", tvaultconf.PASS)
                LOG.debug(
                    "Interval and Next snapshot run time values are correct")
            else:
                reporting.add_test_step(
                    "Verify Interval and Next snapshot run time values are correct", tvaultconf.FAIL)
                raise Exception(
                    "Interval and Next snapshot run time values are incorrect")

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_3_modify_workload_scheduler_enable(self):
        reporting.add_test_script(str(__name__) + "_scheduler_enable")
        try:
            # Prerequisites
            self.created = False
            self.workload_instances = []

            # Launch instance
            self.vm_id = self.create_vm()
            LOG.debug("VM ID-3: " + str(self.vm_id))

            # Create volume
            self.volume_id = self.create_volume()
            LOG.debug("Volume ID-3: " + str(self.volume_id))

            # Attach volume to the instance
            self.attach_volume(self.volume_id, self.vm_id)
            LOG.debug("Volume attached-3")

            # Create workload with scheduler disabled using CLI
            workload_create = command_argument_string.workload_create + \
                " --instance instance-id=" + \
                str(self.vm_id) + " --jobschedule enabled=False"
            rc = cli_parser.cli_returncode(workload_create)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-create command with scheduler disable", tvaultconf.FAIL)
                raise Exception(
                    "Command workload create did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-create command with scheduler disable", tvaultconf.PASS)
                LOG.debug("Command workload create executed correctly")

            time.sleep(10)
            self.wid = query_data.get_workload_id(tvaultconf.workload_name)
            LOG.debug("Workload ID-3: " + str(self.wid))
            if(self.wid != None):
                self.wait_for_workload_tobe_available(self.wid)
                if(self.getWorkloadStatus(self.wid) == "available"):
                    reporting.add_test_step(
                        "Create workload with scheduler disable", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Create workload with scheduler disable", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Create workload with scheduler disable", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            LOG.debug("Workload ID: " + str(self.wid))

            # Verify workload created scheduler disable
            status = self.getSchedulerStatus(self.wid)
            if status:
                reporting.add_test_step(
                    "Verify workload created with scheduler disable", tvaultconf.FAIL)
                raise Exception(
                    "Workload has not been created with scheduler disabled")
            else:
                reporting.add_test_step(
                    "Verify workload created with scheduler disable", tvaultconf.PASS)
                LOG.debug(
                    "Workload created with scheduler disabled successfully")

            # Get workload scheduler details
            schedule_details = self.getSchedulerDetails(self.wid)
            scheduled_start_time = schedule_details['start_time']
            interval = schedule_details['interval']

            # Change global job scheduler to disable
            LOG.debug("Change Global job scheduler to disable")
            status = self.disable_global_job_scheduler()
            if not status:
                reporting.add_test_step(
                    "Global job scheduler disable", tvaultconf.PASS)
                LOG.debug("Global job scheduler disabled successfully")
            else:
                reporting.add_test_step(
                    "Global job scheduler disable", tvaultconf.FAIL)
                raise Exception("Global job scheduler not disabled")

            # Modify workload scheduler to enable
            workload_modify_command = command_argument_string.workload_modify + \
                str(self.wid) + " --jobschedule enabled=True"
            error = cli_parser.cli_error(workload_modify_command)
            if error and (str(error.strip('\n')).find("Cannot update scheduler related fields when global jobscheduler is disabled.") != -1):
                reporting.add_test_step(
                    "Does not execute workload-modify scheduler enable", tvaultconf.PASS)
                LOG.debug("Command executed correctly")
                reporting.add_test_step(
                    "Throws proper message", tvaultconf.PASS)
                LOG.debug("Error message :" + str(error))
            else:
                reporting.add_test_step(
                    "Does not execute workload-modify scheduler enable", tvaultconf.FAIL)
                reporting.add_test_step(
                    "Throws proper message", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")

            # Change global job scheduler to enable
            LOG.debug("Change Global job scheduler to enable")
            status = self.enable_global_job_scheduler()
            if status:
                reporting.add_test_step(
                    "Global job scheduler enable", tvaultconf.PASS)
                LOG.debug("Global job scheduler enabled successfully")
            else:
                reporting.add_test_step(
                    "Global job scheduler enable", tvaultconf.FAIL)
                raise Exception("Global job scheduler not enabled")

            # Modify workload scheduler to enable and set the start date, time and timezone
            now = datetime.datetime.utcnow()
            now_date = datetime.datetime.strftime(now, "%m/%d/%Y")
            now_time = datetime.datetime.strftime(now, "%I:%M %p")
            now_time_plus_15 = now + datetime.timedelta(minutes=15)
            now_time_plus_15 = datetime.datetime.strftime(
                now_time_plus_15, "%I:%M %p")
            workload_modify_command = command_argument_string.workload_modify + str(self.wid) + " --jobschedule enabled=True" + " --jobschedule start_date=" + str(
                now_date) + " --jobschedule start_time=" + "'" + str(now_time_plus_15).strip() + "'" + " --jobschedule timezone=UTC"
            rc = cli_parser.cli_returncode(workload_modify_command)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-modify scheduler enable", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-modify scheduler enable", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            # Verify workload scheduler changed to enable
            self.wait_for_workload_tobe_available(self.wid)
            status = self.getSchedulerStatus(self.wid)
            if status:
                reporting.add_test_step(
                    "Verify workload scheduler enabled", tvaultconf.PASS)
                LOG.debug("workload scheduler enabled successfully")
            else:
                reporting.add_test_step(
                    "Verify workload scheduler enabled", tvaultconf.FAIL)
                LOG.debug("workload scheduler enabled unsuccessfully")

            # Verify interval value and nest_snapshot_run values
            schedule_details = self.getSchedulerDetails(self.wid)
            interval_after_enable = schedule_details['interval']
            next_run_time_after_enable = schedule_details['nextrun']
            next_run_time_after_enable = int(next_run_time_after_enable)
            LOG.debug("interval_after_enable " + str(interval_after_enable))
            LOG.debug("next_run_time_after_enable" +
                      str(next_run_time_after_enable))
            start_date = schedule_details['start_date']
            start_time = schedule_details['start_time']
            date_time = start_date + " " + start_time
            start_date_time = datetime.datetime.strptime(
                date_time, "%m/%d/%Y %H:%M %p")
            LOG.debug("Scheduled start and date time is: " +
                      str(start_date_time))
            utc_24hr = datetime.datetime.utcnow()
            utc_12hr = datetime.datetime.strftime(
                utc_24hr, "%m/%d/%Y %I:%M %p")
            utc_12hr = datetime.datetime.strptime(
                utc_12hr, "%m/%d/%Y %H:%M %p")
            time_diff = (start_date_time - utc_12hr).total_seconds()
            time_diff = int(time_diff)
            LOG.debug(
                "Time difference between UTC time and scheduled start time: " + str(time_diff))
            delta = abs(time_diff - next_run_time_after_enable)

            # Condition for Interval value and time difference should not be more than two minutes
            if delta < 120 and interval == interval_after_enable:
                reporting.add_test_step(
                    "Verify Interval and Next snapshot run time values are correct", tvaultconf.PASS)
                LOG.debug(
                    "Interval and Next snapshot run time values are correct")
            else:
                reporting.add_test_step(
                    "Verify Interval and Next snapshot run time values are correct", tvaultconf.FAIL)
                raise Exception(
                    "Interval and Next snapshot run time values are incorrect")

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

        finally:
            # Delete workload
            status = self.workload_delete(self.wid)
            time.sleep(10)
