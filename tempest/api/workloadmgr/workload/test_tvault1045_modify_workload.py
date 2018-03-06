import sys
import os
sys.path.append(os.getcwd())
from tempest.api.workloadmgr import base
from tempest import config
from tempest import test
from oslo_log import log as logging
from tempest import tvaultconf
from tempest import reporting
from tempest import command_argument_string
from tempest.util import cli_parser
from tempest.util import query_data

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
    def test_tvault1045_modify_workload(self):
	try:
	    #Prerequisites
            self.created = False
            self.workload_instances = []
        
            #Launch instance
            self.vm_id = self.create_vm()
            LOG.debug("VM ID: " + str(self.vm_id))

            #Create volume
            self.volume_id = self.create_volume()
            LOG.debug("Volume ID: " + str(self.volume_id))
        
            #Attach volume to the instance
            self.attach_volume(self.volume_id, self.vm_id)
            LOG.debug("Volume attached")

            #Create workload
            self.workload_instances.append(self.vm_id)
            self.wid = self.workload_create(self.workload_instances, tvaultconf.parallel, workload_name=tvaultconf.workload_name, workload_cleanup=False)
            LOG.debug("Workload ID: " + str(self.wid))
        
            #Launch second instance
            self.vm_id2 = self.create_vm()
            LOG.debug("VM ID2: " + str(self.vm_id2))

            #Create volume
            self.volume_id2 = self.create_volume()
            LOG.debug("Volume ID2: " + str(self.volume_id2))
        
            #Attach volume to the instance
            self.attach_volume(self.volume_id2, self.vm_id2)
            LOG.debug("Volume2 attached")
        
            #Modify workload to add new instance using CLI command        
            workload_modify_command = command_argument_string.workload_modify + "--instance instance-id=" + str(self.vm_id2) + " --instance instance-id=" + str(self.vm_id) + " " + str(self.wid)
            rc = cli_parser.cli_returncode(workload_modify_command)
            if rc != 0:
   	        reporting.add_test_step("Execute workload-modify add one more vm command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
   	        reporting.add_test_step("Execute workload-modify add one more vm command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")
            
            self.wait_for_workload_tobe_available(self.wid)        
            workload_vm_count = query_data.get_available_vms_of_workload(self.wid)
            if (workload_vm_count == 2):
	        reporting.add_test_step("Verification with DB", tvaultconf.PASS)
                LOG.debug("Vm has been added successfully")
            else:
 	        reporting.add_test_step("Verification with DB", tvaultconf.FAIL)
                raise Exception ("Vm has not been added")

	    #Verify workload created scheduler enable
	    status = self.getSchedulerStatus(self.wid)
	    if status:
	        reporting.add_test_step("Workload create with scheduler enabled", tvaultconf.PASS)
		LOG.debug("Workload created with scheduler enabled successfully")
	    else:
		reporting.add_test_step("Workload create with scheduler enabled", tvaultconf.FAIL)
		raise Exception ("Workload has not been created with scheduler enabled")

	    #Change global job scheduler to disable
	    LOG.debug("Change Global job scheduler to disable")
	    status = self.disable_global_job_scheduler()
	    if not status:
	 	reporting.add_test_step("Global job scheduler disable", tvaultconf.PASS)
		LOG.debug("Global job scheduler disabled successfully")
	    else:
		reporting.add_test_step("Global job scheduler disable", tvaultconf.FAIL)
		raise Exception ("Global job scheduler not disabled")

	    #Modify workload scheduler to disable
	    workload_modify_command = command_argument_string.workload_modify + str(self.wid) + " --jobschedule enabled=False"
	    rc = cli_parser.cli_returncode(workload_modify_command)
            if rc != 0:
                reporting.add_test_step("Does not execute workload-modify scheduler disable", tvaultconf.PASS)
		LOG.debug("Command executed correctly")
	    else:
		reporting.add_test_step("Does not execute workload-modify scheduler disable", tvaultconf.FAIL)
		raise Exception("Command did not execute correctly")

	    #Change global job scheduler to enable
            LOG.debug("Change Global job scheduler to enable")
            status = self.enable_global_job_scheduler()
            if status:
                reporting.add_test_step("Global job scheduler enable", tvaultconf.PASS)
                LOG.debug("Global job scheduler enabled successfully")
            else:
                reporting.add_test_step("Global job scheduler enable", tvaultconf.FAIL)
                raise Exception ("Global job scheduler not enabled")

	    #Modify workload scheduler to disable
            workload_modify_command = command_argument_string.workload_modify + str(self.wid) + " --jobschedule enabled=False" 
            rc = cli_parser.cli_returncode(workload_modify_command)
            if rc != 0:
                reporting.add_test_step("Execute workload-modify scheduler disable", tvaultconf.FAIL)
		raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step("Execute workload-modify scheduler disable", tvaultconf.PASS)
		LOG.debug("Command executed correctly")

	    #Verify workload scheduler changed to disable
	    status = self.getSchedulerStatus(self.wid)
	    if status:
		reporting.add_test_step("Verify workload scheduler disabled", tvaultconf.FAIL)
		raise Exception ("workload scheduler disabled unsuccessfully")
	    else:
		reporting.add_test_step("Verify workload scheduler disabled", tvaultconf.PASS)
                LOG.debug("workload scheduler disabled successfully")
	
	    #Delete workload
	    status = self.workload_delete(self.wid)
	    if status:
		reporting.add_test_step("Workload delete", tvaultconf.PASS)
		LOG.debug("workload deleted successfully")
	    else:
		reporting.add_test_step("Workload delete", tvaultconf.FAIL)
		raise Exception ("workload deleted unsuccessfully")

	    #Create workload with scheduler disabled
            self.workload_instances.append(self.vm_id)
            self.wid = self.workload_create(self.workload_instances, tvaultconf.parallel, jobschedule={"enabled": "False"}, workload_name=tvaultconf.workload_name, workload_cleanup=True)
            LOG.debug("Workload ID: " + str(self.wid))

	    #Verify workload created scheduler disable
	    self.wait_for_workload_tobe_available(self.wid)
            status = self.getSchedulerStatus(self.wid)
            if status:
		reporting.add_test_step("Workload create with scheduler disable", tvaultconf.FAIL)
                raise Exception ("Workload has not been created with scheduler disabled")
	    else:
	        reporting.add_test_step("Workload create with scheduler disable", tvaultconf.PASS)
                LOG.debug("Workload created with scheduler disabled successfully")

	    #Change global job scheduler to disable
            LOG.debug("Change Global job scheduler to disable")
            status = self.disable_global_job_scheduler()
            if not status:
                reporting.add_test_step("Global job scheduler disable", tvaultconf.PASS)
                LOG.debug("Global job scheduler disabled successfully")
            else:
                reporting.add_test_step("Global job scheduler disable", tvaultconf.FAIL)
                raise Exception ("Global job scheduler not disabled")

            #Modify workload scheduler to enable
            workload_modify_command = command_argument_string.workload_modify + str(self.wid) + " --jobschedule enabled=True"
            rc = cli_parser.cli_returncode(workload_modify_command)
            if rc != 0:
                reporting.add_test_step("Does not execute workload-modify scheduler enable", tvaultconf.PASS)
                LOG.debug("Command executed correctly")
            else:
                reporting.add_test_step("Does not execute workload-modify scheduler enable", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")

            #Change global job scheduler to enable
            LOG.debug("Change Global job scheduler to enable")
            status = self.enable_global_job_scheduler()
            if status:
                reporting.add_test_step("Global job scheduler enable", tvaultconf.PASS)
                LOG.debug("Global job scheduler enabled successfully")
            else:
                reporting.add_test_step("Global job scheduler enable", tvaultconf.FAIL)
                raise Exception ("Global job scheduler not enabled")
	    
	    #Modify workload scheduler to enable
            workload_modify_command = command_argument_string.workload_modify + str(self.wid) + " --jobschedule enabled=True"
            rc = cli_parser.cli_returncode(workload_modify_command)
            if rc != 0:
                reporting.add_test_step("Execute workload-modify scheduler enable", tvaultconf.FAIL)
                raise Exception ("Command did not execute correctly")
            else:
                reporting.add_test_step("Execute workload-modify scheduler enable", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            #Verify workload scheduler changed to enable
	    self.wait_for_workload_tobe_available(self.wid)
            status = self.getSchedulerStatus(self.wid)
            if status:
	        reporting.add_test_step("Verify workload scheduler enabled", tvaultconf.PASS)
                LOG.debug("workload scheduler enabled successfully")
	    else:
                reporting.add_test_step("Verify workload scheduler enabled", tvaultconf.FAIL)
                raise Exception ("workload scheduler enabled unsuccessfully")
	    
	    reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

