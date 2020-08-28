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
import time

LOG = logging.getLogger(__name__)
CONF = config.CONF

class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
	reporting.add_test_script(str(__name__))

    @test.attr(type='smoke')
    @test.idempotent_id('dbb758aa-b3af-40ac-9105-705b1f18cbd8')
    def test_tvault_rbac_backuprole_touser_policyjson(self):
	try:
	    # Change policy.json file on tvault to change role and rule
	    self.change_policyjson_file("backup", "backup_api")
	    self.instances_id = []
	    
            # Create volume, Launch an Instance
            self.volumes_id = self.create_volume(volume_cleanup=False)
            LOG.debug("Volume-1 ID: " + str(self.volumes_id))
            self.instances_id.append(self.create_vm(vm_cleanup=False))
            LOG.debug("VM-1 ID: " + str(self.instances_id[0]))
            self.attach_volume(self.volumes_id, self.instances_id[0])
            LOG.debug("Volume attached")

            # Use backupuser credentials
	    os.environ['OS_USERNAME']= CONF.identity.backupuser
	    os.environ['OS_PASSWORD']= CONF.identity.backupuser_password

            # Create workload with CLI by backup role
	    workload_create = command_argument_string.workload_create + " --instance instance-id=" +str(self.instances_id[0])
            rc = cli_parser.cli_returncode(workload_create)
            if rc != 0:
		LOG.debug("workload creation unsuccessful by backup role")
                raise Exception ("RBAC policy fails for workload creation by backup role")
	    else:
		LOG.debug("Workload created successfully by backup role")
                reporting.add_test_step("Execute workload_create command by backup role", tvaultconf.PASS)
		time.sleep(10)
		self.wid1 = query_data.get_workload_id(tvaultconf.workload_name)
		workload_available = self.wait_for_workload_tobe_available(self.wid1)

            # Run snapshot_create CLI by backup role
            snapshot_create = command_argument_string.snapshot_create + str(self.wid1)
            LOG.debug("snapshot_create command: " + str(snapshot_create))
            rc = cli_parser.cli_returncode(snapshot_create)
            if rc != 0:
                reporting.add_test_step("Execute snapshot_create command by backup role", tvaultconf.FAIL)
                raise Exception("Command snapshot_create did not execute correctly by backup role")
            else:
                reporting.add_test_step("Execute snapshot_create command by backup role", tvaultconf.PASS)
                LOG.debug("Command snapshot_create executed correctly by backup role")
                self.snapshot_id1 = query_data.get_inprogress_snapshot_id(self.wid1)
                wc = self.wait_for_snapshot_tobe_available(self.wid1, self.snapshot_id1)

	    #Delete the original instance
            self.delete_vm(self.instances_id[0])
            LOG.debug("Instance deleted successfully for restore")

            #Delete corresponding volume
            self.delete_volume(self.volumes_id)
            LOG.debug("Volume deleted successfully for restore")

	    #Create one-click restore using CLI command by backup role
            restore_command = command_argument_string.oneclick_restore + " " + str(self.snapshot_id1)
            rc = cli_parser.cli_returncode(restore_command)
            if rc != 0:
   	        reporting.add_test_step("Execute snapshot-oneclick-restore command by backup role", tvaultconf.FAIL)
                raise Exception("Command one-click restore did not execute correctly by backup role")
            else:
	        reporting.add_test_step("Execute snapshot-oneclick-restore command by backup role", tvaultconf.PASS)
                LOG.debug("Command one-click restore executed correctly backup role")
		wc = self.wait_for_snapshot_tobe_available(self.wid1, self.snapshot_id1)
		self.restore_id1 = query_data.get_snapshot_restore_id(self.snapshot_id1)
                LOG.debug("Restore ID: " + str(self.restore_id1))
		self.restore_vm_id1 = self.get_restored_vm_list(self.restore_id1)
                LOG.debug("Restore VM ID: " + str(self.restore_vm_id1))
                self.restore_volume_id1 = self.get_restored_volume_list(self.restore_id1)
                LOG.debug("Restore Volume ID: " + str(self.restore_volume_id1))
	 
	    # Use admin credentials
	    os.environ['OS_USERNAME']= CONF.identity.username
	    os.environ['OS_PASSWORD']= CONF.identity.password

	    # Create workload with CLI by admin role
            workload_create = command_argument_string.workload_create + " --instance instance-id=" +str(self.restore_vm_id1)
            rc = cli_parser.cli_returncode(workload_create)
            if rc != 0:
                LOG.debug("Command workload_create did not execute correctly by admin role")
		reporting.add_test_step("Can not execute workload_create command by admin role", tvaultconf.PASS)
            else:
                reporting.add_test_step("Command workload_create did not execute correctly by admin role", tvaultconf.FAIL)
		raise Exception("Command workload_create executed correctly by admin role")

	    # Run snapshot_create CLI by admin role
            snapshot_create = command_argument_string.snapshot_create + str(self.wid1)
            LOG.debug("snapshot_create command: " + str(snapshot_create))
            rc = cli_parser.cli_returncode(snapshot_create)
            if rc != 0:
                reporting.add_test_step("Can not execute snapshot_create command by admin role", tvaultconf.PASS)
                LOG.debug("Command snapshot_create did not execute correctly by admin role")
            else:
                reporting.add_test_step("Can not execute snapshot_create command by admin role", tvaultconf.FAIL)
                raise Exception("Command snapshot_create executed correctly by admin role") 

	    #Create one-click restore using CLI command by admin role
            restore_command = command_argument_string.oneclick_restore + " " + str(self.snapshot_id1)
            rc = cli_parser.cli_returncode(restore_command)
            if rc != 0:
		reporting.add_test_step("Can not execute restore_create command by admin role", tvaultconf.PASS)
                LOG.debug("Command restore_create did not execute correctly by admin role")
            else:
	        reporting.add_test_step("Can not execute restore_create command by admin role", tvaultconf.FAIL)
                raise Exception("Command restore_create executed correctly by admin role")
	    
	    # Run restore_delete CLI by admin role
            restore_delete = command_argument_string.restore_delete + str(self.restore_id1)
            rc = cli_parser.cli_returncode(restore_delete)
            if rc != 0:
                reporting.add_test_step("Can not execute restore_delete command by admin role", tvaultconf.PASS)
                LOG.debug("Command restore_delete did not execute correctly by admin role")
            else:
                reporting.add_test_step("Can not execute restore_delete command by admin role", tvaultconf.FAIL)
                raise Exception("Command restore_delete executed correctly by admin role")

	    # Run snapshot_delete CLI by admin role
            snapshot_delete = command_argument_string.snapshot_delete + str(self.snapshot_id1)
            rc = cli_parser.cli_returncode(snapshot_delete)
            if rc != 0:
                reporting.add_test_step("Can not execute snapshot_delete command by admin role", tvaultconf.PASS)
                LOG.debug("Command snapshot_delete did not execute correctly by admin role")
            else:
                reporting.add_test_step("Can not execute snapshot_delete command by admin role", tvaultconf.FAIL)
                raise Exception("Command snapshot_delete executed correctly by admin role")

	    # Delete workload with CLI by admin role
            workload_delete = command_argument_string.workload_delete + str(self.wid1)
            rc = cli_parser.cli_returncode(workload_delete)
            if rc != 0:
                reporting.add_test_step("Can not execute workload_delete command by admin role", tvaultconf.PASS)
                LOG.debug("Command workload_delete did not execute correctly by admin role")
	    else:
                reporting.add_test_step("Can not execute workload_delete command by admin role", tvaultconf.FAIL)
		raise Exception("Command workload_delete executed correctly by admin role")
	    
	    # Use nonadmin credentials
	    os.environ['OS_USERNAME']= CONF.identity.nonadmin_user
	    os.environ['OS_PASSWORD']= CONF.identity.nonadmin_password

	    # Create workload with CLI by default role
            workload_create = command_argument_string.workload_create + " --instance instance-id=" +str(self.restore_vm_id1)
            rc = cli_parser.cli_returncode(workload_create)
            if rc != 0:
                LOG.debug("Command workload_create did not execute correctly by default role")
                reporting.add_test_step("Can not execute workload_create command by default role", tvaultconf.PASS)
            else:
                reporting.add_test_step("Can not execute workload_create command by default role", tvaultconf.FAIL)
                raise Exception("Command workload_create executed correctly by default role")
            
	    # Run snapshot_create CLI by default role
            snapshot_create = command_argument_string.snapshot_create + str(self.wid1)
            rc = cli_parser.cli_returncode(snapshot_create)
            if rc != 0:
                reporting.add_test_step("Can not execute snapshot_create command by default role", tvaultconf.PASS)
                LOG.debug("Command snapshot_create did not execute correctly by default role")
            else:
                reporting.add_test_step("Can not execute snapshot_create command by default role", tvaultconf.FAIL)
                raise Exception("Command snapshot_create executed correctly by default role")
	
	    # Create one-click restore using CLI by default role
            restore_command = command_argument_string.oneclick_restore + " " + str(self.snapshot_id1)
            rc = cli_parser.cli_returncode(restore_command)
            if rc != 0:
                reporting.add_test_step("Can not execute restore_create command by default role", tvaultconf.PASS)
                LOG.debug("Command restore_create did not execute correctly by default role")
            else:
                reporting.add_test_step("Can not execute restore_create command by default role", tvaultconf.FAIL)
                raise Exception("Command restore_create executed correctly by default role")	

	    # Run restore_delete CLI by default role
            restore_delete = command_argument_string.restore_delete + str(self.restore_id1)
            rc = cli_parser.cli_returncode(restore_delete)
            if rc != 0:
                reporting.add_test_step("Can not execute restore_delete command by default role", tvaultconf.PASS)
                LOG.debug("Command restore_delete did not execute correctly by default role")
            else:
                reporting.add_test_step("Can not execute restore_delete command by default role", tvaultconf.FAIL)
                raise Exception("Command restore_delete executed correctly by default role")

            # Run snapshot_delete CLI by default role
            snapshot_delete = command_argument_string.snapshot_delete + str(self.snapshot_id1)
            LOG.debug("snapshot_delete command: " + str(snapshot_create))
            rc = cli_parser.cli_returncode(snapshot_delete)
            if rc != 0:
                reporting.add_test_step("Can not execute snapshot_delete command by default role", tvaultconf.PASS)
                LOG.debug("Command snapshot_delete did not execute correctly by default role")
            else:
                reporting.add_test_step("Can not execute snapshot_delete command by default role", tvaultconf.FAIL)
                raise Exception("Command snapshot_delete executed correctly by default role")
	
	    # Delete workload with CLI by default role
            workload_delete = command_argument_string.workload_delete + str(self.wid1)
            rc = cli_parser.cli_returncode(workload_delete)
            if rc != 0:
                reporting.add_test_step("Can not execute workload_delete command by default role", tvaultconf.PASS)
                LOG.debug("Command workload_delete did not execute correctly by default role")
            else:
		reporting.add_test_step("Can not execute workload_delete command by default role", tvaultconf.FAIL)
                raise Exception("Command workload_delete executed correctly by default role")

	    # Use backupuser credentials
	    os.environ['OS_USERNAME']= CONF.identity.backupuser
	    os.environ['OS_PASSWORD']= CONF.identity.backupuser_password
	
	    # Run restore_delete CLI by backup role
            restore_delete = command_argument_string.restore_delete + str(self.restore_id1)
            rc = cli_parser.cli_returncode(restore_delete)
            if rc != 0:
                reporting.add_test_step("Execute  restore_delete command by backup role", tvaultconf.FAIL)
                raise Exception("Command  restore_delete did not execute correctly by backup role")
            else:
                reporting.add_test_step("Execute restore_delete command by backup role", tvaultconf.PASS)
                LOG.debug("Command restore_delete executed correctly by backup role")
		wc = self.wait_for_snapshot_tobe_available(self.wid1, self.snapshot_id1)
		#Delete restored VM instance and volume
                self.delete_restored_vms(self.restore_vm_id1, self.restore_volume_id1)
                LOG.debug("Restored VMs deleted successfully by backup role")

            # Run snapshot_delete CLI by backup role
            snapshot_delete = command_argument_string.snapshot_delete + str(self.snapshot_id1)
            LOG.debug("snapshot_delete command: " + str(snapshot_create))
            rc = cli_parser.cli_returncode(snapshot_delete)
            if rc != 0:
                reporting.add_test_step("Execute snapshot_delete command by backup role", tvaultconf.FAIL)
                raise Exception("Command snapshot_delete did not execute correctly by backup role")
            else:
                reporting.add_test_step("Execute snapshot_delete command by backup role", tvaultconf.PASS)
                LOG.debug("Command snapshot_delete executed correctly by backup role")
		workload_available = self.wait_for_workload_tobe_available(self.wid1)	

	    # Delete workload with CLI by backup role
            workload_delete = command_argument_string.workload_delete + str(self.wid1)
            rc = cli_parser.cli_returncode(workload_delete)
            if rc != 0:
		reporting.add_test_step("Execute workload_delete command by backup role", tvaultconf.FAIL)
                raise Exception ("RBAC policy fails for workload deletion by backup role")
            else:
                LOG.debug("Workload deleted successfully by backup role")
                reporting.add_test_step("Execute workload_delete command by backup role", tvaultconf.PASS)

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

