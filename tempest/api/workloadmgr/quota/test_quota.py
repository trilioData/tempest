from tempest.util import query_data
from tempest.util import cli_parser
from tempest import command_argument_string
from tempest import reporting
from tempest import tvaultconf
from oslo_log import log as logging
from tempest.lib import decorators
from tempest import config
from tempest.api.workloadmgr import base
import sys
import os
sys.path.append(os.getcwd())

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    @decorators.attr(type='workloadmgr_api')
    def test_01_list_quota_type(self):
        reporting.add_test_script(str(__name__) + "_list_quota_type")
        try:
            # List available workload types using CLI command
            rc = cli_parser.cli_returncode(
                command_argument_string.quota_type_list)
            if rc != 0:
                reporting.add_test_step(
                    "Execute project-quota-type-list command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute project-quota-type-list command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            wc = query_data.get_available_project_quota_types()
            out = cli_parser.cli_output(
                command_argument_string.quota_type_list)
            if (int(wc) == int(out)):
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.PASS)
                LOG.debug(
                    "Project quota type list command listed available quota types correctly")
            else:
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.FAIL)
                raise Exception(
                    "Project quota type list command did not list available quota types correctly")
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
