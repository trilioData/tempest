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
    def test_create_license(self):
	#Create license using CLI command
	self.cmd = command_argument_string.license_create + tvaultconf.vm_license_filename
        LOG.debug("License create command: " + str(self.cmd))
        rc = cli_parser.cli_returncode(self.cmd)
        if rc != 0:
    	    reporting.add_test_step("Execute license_create command", tvaultconf.FAIL)
	    reporting.set_test_script_status(tvaultconf.FAIL)
            raise Exception("Command did not execute correctly")
        else:
	    reporting.add_test_step("Execute license_create command", tvaultconf.PASS)
            LOG.debug("Command executed correctly")
           
	#Verification
	self.license_data = self.get_license_list()
	LOG.debug("License data returned: " + str(self.license_data))
	if(len(self.license_data.keys()) != 0):
            reporting.add_test_step("License verification", tvaultconf.PASS)
        else:
            reporting.add_test_step("License verification", tvaultconf.FAIL)
	    reporting.set_test_script_status(tvaultconf.FAIL)
            raise Exception("License not added") 
        reporting.test_case_to_write()
