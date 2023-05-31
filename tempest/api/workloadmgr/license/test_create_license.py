import os
import sys

from oslo_log import log as logging

from tempest import command_argument_string
from tempest import config
from tempest import reporting
from tempest import tvaultconf
from tempest.api.workloadmgr import base
from tempest.lib import decorators
from tempest.util import cli_parser

sys.path.append(os.getcwd())

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()
        reporting.add_test_script(str(__name__))

    @decorators.attr(type='workloadmgr_cli')
    def test_create_license(self):
        try:
            # Create license using CLI command
            self.cmd = command_argument_string.license_create + tvaultconf.compute_license_filename
            LOG.debug("License create command: " + str(self.cmd))
            rc = cli_parser.cli_expect(self.cmd,
                [tvaultconf.create_license_expected_str],
                [tvaultconf.create_license_send_str])
            if rc:
                reporting.add_test_step(
                    "Execute license_create command", tvaultconf.PASS)
            else:
                raise Exception("Execute license_create command")

            # Verification
            self.license_data = self.get_license_list()
            LOG.debug("License data returned: " + str(self.license_data))
            if(len(self.license_data.keys()) != 0):
                reporting.add_test_step("License verification", tvaultconf.PASS)
            else:
                raise Exception("License verification")
        except Exception as e:
            reporting.add_test_step(ste(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

