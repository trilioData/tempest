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

class RestoreTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(RestoreTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
	reporting.add_test_script(str(__name__))

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_tvault1290_delete_restore(self):
	try:
	    #Prerequisites
            self.created = False
            self.workload_instances = []
        
            #Launch instance
            self.vm_id = self.create_vm(vm_cleanup=False)
            LOG.debug("VM ID: " + str(self.vm_id))

            #Create volume
            self.volume_id = self.create_volume(volume_cleanup=False)
            LOG.debug("Volume ID: " + str(self.volume_id))
        
            #Attach volume to the instance
            self.attach_volume(self.volume_id, self.vm_id, attach_cleanup=False)
            LOG.debug("Volume attached")

            #Create workload
            self.workload_instances.append(self.vm_id)
            self.wid = self.workload_create(self.workload_instances, tvaultconf.parallel, workload_name=tvaultconf.workload_name)
            LOG.debug("Workload ID: " + str(self.wid))
            time.sleep(5)
        
            #Create snapshot
            self.snapshot_id = self.workload_snapshot(self.wid, True, tvaultconf.snapshot_name)
            LOG.debug("Snapshot ID: " + str(self.snapshot_id))
        
            #Wait till snapshot is complete
            wc = query_data.get_workload_snapshot_status(tvaultconf.snapshot_name,tvaultconf.snapshot_type_full, self.snapshot_id)
            LOG.debug("Workload snapshot status: " + str(wc))
            while (str(wc) != "available" or str(wc)!= "error"):
                time.sleep(5)
                wc = query_data.get_workload_snapshot_status(tvaultconf.snapshot_name, tvaultconf.snapshot_type_full, self.snapshot_id)
                LOG.debug("Workload snapshot status: " + str(wc))
                if (str(wc) == "available"):
                    LOG.debug("Workload snapshot successfully completed")
                    self.created = True
                    break
                else:
                    if (str(wc) == "error"):
                        break
            if (self.created == False):
                raise Exception ("Workload snapshot did not get created")
        
            #Delete instance
            self.delete_vm(self.vm_id)
            LOG.debug("Instance deleted successfully")
        
            #Delete corresponding volume
            self.delete_volume(self.volume_id)
            LOG.debug("Volume deleted successfully")
        
            #Create one-click restore
            self.restore_id = self.snapshot_restore(self.wid, self.snapshot_id, tvaultconf.restore_name, restore_cleanup=False)
            LOG.debug("Restore ID: " + str(self.restore_id))
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id)
 
            self.restore_vm_id = self.get_restored_vm_list(self.restore_id)
            LOG.debug("Restore VM ID: " + str(self.restore_vm_id))
        
            self.restore_volume_id = self.get_restored_volume_list(self.restore_id)
            LOG.debug("Restore Volume ID: " + str(self.restore_volume_id))        
        
            #Delete restore for snapshot using CLI command
            rc = cli_parser.cli_returncode(command_argument_string.restore_delete + self.restore_id)
            if rc != 0:
	        reporting.add_test_step("Execute restore-delete command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
  	        reporting.add_test_step("Execute restore-delete command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")
            time.sleep(5)
        
            wc = query_data.get_snapshot_restore_delete_status(tvaultconf.restore_name,tvaultconf.restore_type)
            if (str(wc) == "1"):
	        reporting.add_test_step("Verification", tvaultconf.PASS)
                LOG.debug("Snapshot restore successfully deleted")
            else:
   	        reporting.add_test_step("Verification", tvaultconf.FAIL)
                raise Exception ("Restore did not get deleted")
        
            #Cleanup
            #Delete restored VM instance and volume
            self.delete_restored_vms(self.restore_vm_id, self.restore_volume_id)
            LOG.debug("Restored VMs deleted successfully")
	    reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
