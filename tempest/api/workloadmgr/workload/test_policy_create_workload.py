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
    wid=""
    vm_id=""
    volume_id=""
    policy_id=""

    @classmethod
    def setup_clients(cls):
        super(ScehdulerPolicyTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
	#reporting.add_test_script(str(__name__))

    @test.pre_req({'type':'small_workload'})
    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_1_policy_create_workload(self):
        reporting.add_test_script(str(__name__) + "_workload_policy")
        try:
	    global wid
            global vm_id
            global volume_id
            global policy_id
            vm_id = self.vm_id
            volume_id = self.volume_id
            #create scehdular policy
            policy_id = self.create_scheduler_policy(
                                                          policy_name = tvaultconf.policy_name, 
                                                          fullbackup_interval = tvaultconf.fullbackup_interval,
                                                          interval = tvaultconf.interval, 
                                                          retention_policy_value = tvaultconf.retention_policy_value,
                                                          retention_policy_type = tvaultconf.retention_policy_type, 
                                                          description='test'
                                                         )
            if policy_id != None:
                reporting.add_test_step("Create workload policy", tvaultconf.PASS)
                LOG.debug("Scheduler policy id is "+str(policy_id))   
            else:
                reporting.add_test_step("Create workload policy", tvaultconf.FAIL)
                LOG.debug("Scheduler policy is not assigned created")
                raise Exception("Workload policy is not created")
            
            #Assign workload policy to projects
            admin_project_id = CONF.identity.admin_tenant_id 
            policy_id = self.assign_workload_policy(policy_id,add_project_ids_list=[admin_project_id],remove_project_ids_list=[])
            if policy_id != None:
                reporting.add_test_step("Assign workload policy", tvaultconf.PASS)
                LOG.debug("Scheduler polciy is assigned to project successfully")
            else:
                reporting.add_test_step("Assign workload policy", tvaultconf.FAIL)
                LOG.debug("Schedulaer policy is not assigned correctly")
                raise Exception("Workload policy is not assigned correctly")
 
            #Create workload with CLI command
            workload_create = command_argument_string.workload_create + " --instance instance-id=" +str(self.vm_id) + " --policy-id " + str(policy_id)

	    LOG.debug("workload_create command: " + str(workload_create))
	
            rc = cli_parser.cli_returncode(workload_create)
            if rc != 0:
	        reporting.add_test_step("Execute workload-create command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
	        reporting.add_test_step("Execute workload-create command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

	    time.sleep(10)
	    wid = query_data.get_workload_id(tvaultconf.workload_name)
            LOG.debug("Workload ID: " + str(wid))
	    if(wid != None):
		self.wait_for_workload_tobe_available(wid)
		if(self.getWorkloadStatus(wid) == "available"):
                    reporting.add_test_step("Create workload", tvaultconf.PASS)
	        else:
                    reporting.add_test_step("Create workload", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
	    else:
		reporting.add_test_step("Create workload", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            #get workload details for verifcation steps
            policy_id_of_workload = self.get_policy_idof_workload(wid)
            LOG.debug("workload policy id is : " + str(policy_id_of_workload))
            if str(policy_id_of_workload).strip() == str(policy_id).strip():
                reporting.add_test_step("Workload is created with policy",tvaultconf.PASS)
            else:
                reporting.add_test_step("Workload is created with policy",tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            '''
            workload_details=self.getWorkloadDetails(wid)
            LOG.debug("Workload Details: "+str(workload_details))
            policy_id_of_workload = str(
            
            fullbackup_interval = str(workload_details['fullbackup_interval']).strip()
            interval = str(workload_details['interval']).strip()
            retention_policy_value = str(workload_details['retention_policy_value']).strip()
            retention_policy_type = str(workload_details['retention_policy_type']).strip()
            LOG.debug("fullbackup interval: "+str(fullbackup_interval)+", interval : "+str(interval)+"retention_policy_value : "+str(retention_policy_value))

            #verify workload is created with same values that we defined in policy.(policy should apply on workload at tym of creation)
            
            if fullbackup_interval == tvaultconf.fullbackup_interval:
                reporting.add_test_step("Compare Fullbackup_interval values of workload and policy",tvaultconf.PASS)
            else:
                reporting.add_test_step("Compare Fullbackup_interval values of workload and policy",tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            if interval == tvaultconf.interval:
                reporting.add_test_step("Compare interval values of workload and policy",tvaultconf.PASS)
            else:
                reporting.add_test_step("Compare interval values of workload and policy",tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            if retention_policy_value == tvaultconf.retention_policy_value:
                reporting.add_test_step("Compare reteniton_policy_value of workload and policy",tvaultconf.PASS)
            else:
                reporting.add_test_step("Compare retention policy_value of workload and policy",tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
           
            if retention_policy_type == tvaultconf.retention_policy_type:
                reporting.add_test_step("Compare reteniton_policy_type values of workload and policy",tvaultconf.PASS)
            else:
                reporting.add_test_step("Compare retention_policy_type values of workload and policy",tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            '''

            #LOG.debug("can not create log")
            workload_modify_command = command_argument_string.workload_modify +  " --jobschedule retention_policy_value="+"12" +" --jobschedule interval="+"4hrs" + " --jobschedule enabled=True "+ str(wid)             
            rc = cli_parser.cli_returncode(workload_modify_command)
            LOG.debug("rc value is : "+ str(rc))
            if rc ==0:
                reporting.add_test_step("Execute workload-modify command", tvaultconf.FAIL)
                raise Exception("updated scheduler settings even though policies are applied on project")
            else:
                reporting.add_test_step("Execute workload-modify command", tvaultconf.PASS)
                LOG.debug("modify-workload command returns error as expected")

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
    
    #scenario -2
    #verify retention is working as per mention policy 
    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_2_retention_verification(self):
        reporting.add_test_script(str(__name__) + "_policy_retention")
        try:            
            global wid
            global vm_id
            global volume_id
            global policy_id
            snapshots_list = []
            LOG.debug("wid is : "+str(wid))
            for i in range(1, tvaultconf.number_of_snapshots_to_create+1):
                snapshot_id = self.workload_snapshot(wid,True,snapshot_name=tvaultconf.snapshot_name+str(i),snapshot_cleanup=False) 
                snapshots_list.append(snapshot_id)
            LOG.debug("snapshot id list is : "+str(snapshots_list))    
            
            #create one more snapshot 
            snapshot_id = self.workload_snapshot(wid,True,snapshot_name=tvaultconf.snapshot_name+"_final",snapshot_cleanup=False)
            LOG.debug("Last snapshot id is : " + str(snapshot_id))
            snapshots_list.append(snapshot_id)
            LOG.debug("final snapshot list is "+str(snapshots_list))
     
            #get snapshot count and snapshot_details
            snapshot_list_of_workload = self.getSnapshotList(wid)                        
            LOG.debug("snapshot list retrived from API is : " + str(snapshot_list_of_workload))
            
            #verify that numbers of snapshot created persist retention_policy_value
            LOG.debug("number of snapshots created : %d "%len(snapshot_list_of_workload))
            if int(tvaultconf.retention_policy_value) == len(snapshot_list_of_workload):
                reporting.add_test_step("number of snapshots created not exceeding retention_policy_value", tvaultconf.PASS)
                
            else:
                reporting.add_test_step("number of snapshots created not exceeding retention_policy_value", tvaultconf.FAIL)
                LOG.debug("verify that numbers of snapshot created are not greater than policy_retention value")
                raise Exception("number of snapshot created should not exceed retention_policy_value")
                reporting.set_test_script_status(tvaultconf.FAIL)
               
            #check if first snapshot is deleted or not 
            deleted_snapshot_id = snapshots_list[0]
            LOG.debug("snapshot id of first snapshot is : "+str(deleted_snapshot_id))
           
            is_first_snapshot_not_deleted = False
            for i in range(0,len(snapshot_list_of_workload)):
                if deleted_snapshot_id == snapshot_list_of_workload[i]:
                    is_first_snapshot_not_deleted = True
                    break
                else:
                    is_first_snapshot_not_deleted = False

            LOG.debug("check if first snapshots is deleted : %d" %is_first_snapshot_not_deleted)
            if is_first_snapshot_not_deleted==False:
                reporting.add_test_step("check first snapshot gets deleted", tvaultconf.PASS)
            else:
                reporting.add_test_step("check first snapshot gets deleted", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("first snapshot should get deleted when we are trying to execeed reteintion_policy_value")

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

        finally:            
            #Cleanup            
            #delete vm 
            self.delete_vm(vm_id)
            LOG.debug("virtual machine deleted succesfully")

            #delete volume
            self.delete_volume(volume_id)
            LOG.debug("volume deleted successfully")     

            #Delete snapshot
            for i in range(0,len(snapshot_list_of_workload)):
                self.snapshot_delete(wid,snapshot_list_of_workload[i])
            LOG.debug("snapshot deleted successfullly")

            #Delete workload
            self.workload_delete(wid)
            LOG.debug("Workload deleted successfully")
                     
            #Delete workload policy
            is_policy_deleted = self.delete_scheduler_policy(policy_id)
            LOG.debug("Scheduler policy deleted successfull %s" % is_policy_deleted )
	    reporting.test_case_to_write()


