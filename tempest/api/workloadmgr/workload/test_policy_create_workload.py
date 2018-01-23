import sys
import os
sys.path.append(os.getcwd())
from tempest.api.workloadmgr import base
from tempest import config
from tempest import test
from oslo_log import log as logging
from tempest import tvaultconf
from tempest import reporting
import time
from tempest import command_argument_string
from tempest.util import cli_parser
from tempest.util import query_data

LOG = logging.getLogger(__name__)
CONF = config.CONF

class ScehdulerPolicyTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(ScehdulerPolicyTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
	reporting.add_test_script(str(__name__))

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_policy_create_workload(self):
	try:
	    #Prerequisites
            self.created = False

            #Launch instance
            self.vm_id = self.create_vm()
            LOG.debug("VM ID: " + str(self.vm_id))

            #Create volume
            self.volume_id = self.create_volume()
            LOG.debug("Volume ID: " + str(self.volume_id))
        
            #Attach volume to the instance
            self.attach_volume(self.volume_id, self.vm_id)
            LOG.debug("Volume attached")
            
            #create scehdular policy
            self.policy_id = self.create_scheduler_policy(
                                                          policy_name = tvaultconf.policy_name, 
                                                          fullbackup_interval = tvaultconf.fullbackup_interval,
                                                          interval = tvaultconf.interval, 
                                                          retention_policy_value = tvaultconf.retention_policy_value,
                                                          retention_policy_type = tvaultconf.retention_policy_type, 
                                                          description='test'
                                                         )
            if self.policy_id != None:
                reporting.add_test_step("Create workload policy", tvaultconf.PASS)
                LOG.debug("Scheduler policy id is "+str(self.policy_id))   
            else:
                reporting.add_test_step("Create workload policy", tvaultconf.FAIL)
                LOG.debug("Scheduler policy is not assigned created")
                raise Exception("Workload policy is not created")
            
            #Assign workload policy to projects
            admin_project_id = CONF.identity.admin_tenant_id 
            self.policy_id = self.assign_workload_policy(self.policy_id,add_project_ids_list=[admin_project_id],remove_project_ids_list=[])
            if self.policy_id != None:
                reporting.add_test_step("Assign workload policy", tvaultconf.PASS)
                LOG.debug("Scheduler polciy is assigned to project successfully")
            else:
                reporting.add_test_step("Assign workload policy", tvaultconf.FAIL)
                LOG.debug("Schedulaer policy is not assigned correctly")
                raise Exception("Workload policy is not assigned correctly")
 
            #Create workload with CLI command
            workload_create = command_argument_string.workload_create + " --instance instance-id=" +str(self.vm_id) + " --policy-id " + str(self.policy_id)

	    LOG.debug("workload_create command: " + str(workload_create))
	
            rc = cli_parser.cli_returncode(workload_create)
            if rc != 0:
	        reporting.add_test_step("Execute workload-create command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
	        reporting.add_test_step("Execute workload-create command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

	    time.sleep(10)
	    self.wid = query_data.get_workload_id(tvaultconf.workload_name)
            LOG.debug("Workload ID: " + str(self.wid))
	    if(self.wid != None):
		self.wait_for_workload_tobe_available(self.wid)
		if(self.getWorkloadStatus(self.wid) == "available"):
                    reporting.add_test_step("Create workload", tvaultconf.PASS)
	        else:
                    reporting.add_test_step("Create workload", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
	    else:
		reporting.add_test_step("Create workload", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)


            #Cleanup
            #Delete workload
            self.workload_delete(self.wid)
            LOG.debug("Workload deleted successfully")

            #Delete workload policy
            #is_policy_deleted = self.delete_scheduler_policy(self.policy_id)
            #LOG.debug("Scheduler policy deleted successfull %s" % is_policy_deleted )
	    reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
