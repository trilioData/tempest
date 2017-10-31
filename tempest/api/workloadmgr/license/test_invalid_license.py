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
    def test_invalid_license(self):
	try:
	    #Create license using CLI command
  	    self.cmd = command_argument_string.license_create + tvaultconf.invalid_license_filename
            LOG.debug("License create command: " + str(self.cmd))
            rc = cli_parser.cli_returncode(self.cmd)
            if rc != 0:
    	        reporting.add_test_step("Execute license_create command with invalid license", tvaultconf.PASS)
                LOG.debug("Command executed correctly")
            else:
	        reporting.add_test_step("Execute license_create command with invalid license", tvaultconf.FAIL)
                raise Exception("Command not executed correctly")

	    self.license_txt = ""
    	    #Get license key content
	    with open(tvaultconf.invalid_license_filename) as f:
	        for line in f:
	            self.license_txt += line
	    LOG.debug("License text: " + str(self.license_txt))
	    out = self.create_license(self.license_txt)
	    LOG.debug("license-create API output: " + str(out))
	    if(str(out).find('Cannot verify the license signature') != -1):
		reporting.add_test_step("Verify error message", tvaultconf.PASS)
	    else:
		reporting.add_test_step("Verify error message", tvaultconf.FAIL)
                raise Exception("Incorrect error message displayed")
            reporting.test_case_to_write()
	except Exception as e:
	    LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
