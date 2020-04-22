from tempest.util import query_data
from tempest.util import cli_parser
from tempest import command_argument_string
from tempest import reporting
from tempest import tvaultconf
from oslo_log import log as logging
from tempest import test
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
        cls.client = cls.os.wlm_client
        reporting.add_test_script(str(__name__))

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_tvault1031_show_workloadtype(self):
        try:
            # Get workload type details using CLI command
            rc = cli_parser.cli_returncode(
                command_argument_string.workload_type_show)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-type-show command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-type-show command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            db_resp = query_data.get_workload_type_data(
                tvaultconf.workload_type_id)
            LOG.debug("Response from DB: " + str(db_resp))
            cmd_resp = cli_parser.cli_output(
                command_argument_string.workload_type_show)
            LOG.debug("Response from CLI: " + str(cmd_resp))

            if(db_resp[5] == tvaultconf.workload_type_id):
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.PASS)
                LOG.debug("Workload type response from CLI and DB match")
            else:
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.FAIL)
                raise Exception(
                    "Workload type response from CLI and DB do not match")
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
