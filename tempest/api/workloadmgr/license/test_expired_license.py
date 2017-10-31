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
    def test_expired_license(self):
	try:
            #Create license using CLI command
            self.cmd = command_argument_string.license_create + tvaultconf.expired_license_filename
            LOG.debug("License create command: " + str(self.cmd))
            rc = cli_parser.cli_returncode(self.cmd)
            LOG.debug("rc value: " + str(rc))
            if rc != 0:
                reporting.add_test_step("Execute license_create command with expired license", tvaultconf.FAIL)
                raise Exception("Command not executed correctly")
            else:
                reporting.add_test_step("Execute license_create command with expired license", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            out = self.get_license_check()
            LOG.debug("license-check API output: " + str(out))
            if(str(out).find('License expired') != -1):
                reporting.add_test_step("Verify license expiration message", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify license expiration message", tvaultconf.FAIL)
                raise Exception("Incorrect license expiration message displayed")
            reporting.test_case_to_write()
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

