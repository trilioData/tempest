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
    def test_license_check(self):
	try:
	    #Create license using CLI command
  	    self.cmd = command_argument_string.license_create + tvaultconf.vm_license_filename
            rc = cli_parser.cli_returncode(self.cmd)
            if rc != 0:
    	        reporting.add_test_step("Apply 10VM license", tvaultconf.FAIL)
	        reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
	        reporting.add_test_step("Apply 10VM license", tvaultconf.PASS)
        
 	    #Create simple workload
	    self.workload_instances = []
    	    for i in range(0,2):
	        self.vm_id = self.create_vm()
	        self.volume_id = self.create_volume()
	        self.attach_volume(self.volume_id, self.vm_id)
	        self.workload_instances.append(self.vm_id)
	    self.wid = self.workload_create(self.workload_instances, tvaultconf.parallel)
	    LOG.debug("Workload ID: " + str(self.wid))
	
  	    #Verify license-check CLI command
            self.cmd = command_argument_string.license_check
            rc = cli_parser.cli_returncode(self.cmd)
            if rc != 0:
                reporting.add_test_step("Execute license-check command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step("Execute license-check command", tvaultconf.PASS)

	    #Verification
	    out = cli_parser.cli_output(self.cmd)
            LOG.debug("CLI Response: " + str(out))
	    if(str(out).find('2') != -1):
                reporting.add_test_step("License-check verification", tvaultconf.PASS)
            else:
                reporting.add_test_step("License-check verification", tvaultconf.FAIL)
                raise Exception("License-check verification failed") 
            reporting.test_case_to_write()
	except Exception as e:
	    LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
