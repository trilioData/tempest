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

class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
	reporting.add_test_script(str(__name__))

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_tvault1292_create_full_snapshot(self):
	try:
	    #Prerequisites
	    self.created = False
            self.workload_instances = []
        
            #Launch instance
            self.vm_id = self.create_vm()
            LOG.debug("VM ID: " + str(self.vm_id))

            #Create volume
            self.volume_id = self.create_volume(tvaultconf.volume_size,tvaultconf.volume_type)
            LOG.debug("Volume ID: " + str(self.volume_id))
        
            #Attach volume to the instance
            self.attach_volume(self.volume_id, self.vm_id)
            LOG.debug("Volume attached")

            #Create workload
            self.workload_instances.append(self.vm_id)
            self.wid = self.workload_create(self.workload_instances, tvaultconf.parallel, workload_name=tvaultconf.workload_name)
            LOG.debug("Workload ID: " + str(self.wid))
            time.sleep(5)
                
            #Create snapshot with CLI command
            create_snapshot = command_argument_string.snapshot_create + self.wid
            LOG.debug("Create snapshot command: " + str(create_snapshot))
            rc = cli_parser.cli_returncode(create_snapshot)
            if rc != 0:
    	        reporting.add_test_step("Execute workload-snapshot command with --full", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
  	        reporting.add_test_step("Execute workload-snapshot command with --full", tvaultconf.PASS)
                LOG.debug("Command executed correctly")
               
            self.snapshot_id = query_data.get_inprogress_snapshot_id(self.wid)
            LOG.debug("Snapshot ID: " + str(self.snapshot_id))
               
            wc = self.wait_for_snapshot_tobe_available(self.wid,self.snapshot_id)
            if (str(wc) == "available"):
   	        reporting.add_test_step("Full snapshot", tvaultconf.PASS)
                LOG.debug("Workload snapshot successfully completed")
                self.created = True
            else:
                if (str(wc) == "error"):
                    pass
            if (self.created == False):
   	        reporting.add_test_step("Full snapshot", tvaultconf.FAIL)
                raise Exception ("Workload snapshot did not get created")
        
            #Cleanup
            #Delete snapshot
            self.snapshot_delete(self.wid, self.snapshot_id)
            LOG.debug("Snapshot deleted successfully")
	    reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
