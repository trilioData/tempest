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
from tempest.util import query_data

sys.path.append(os.getcwd())

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    @decorators.attr(type='workloadmgr_cli')
    def test_01_list_quota_type(self):
        reporting.add_test_script(str(__name__) + "_list_quota_type_cli")
        try:
            rc = cli_parser.cli_returncode(
                command_argument_string.quota_type_list)
            if rc != 0:
                raise Exception("Execute project-quota-type-list command")
            else:
                reporting.add_test_step(
                    "Execute project-quota-type-list command", tvaultconf.PASS)

            wc = query_data.get_available_project_quota_types()
            out = cli_parser.cli_output(
                command_argument_string.quota_type_list)
            if (int(wc) == int(out)):
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.PASS)
            else:
                raise Exception("Verification with DB")
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_02_list_quota_type(self):
        reporting.add_test_script(str(__name__) + "_list_quota_type_api")
        try:
            quota_list = self.get_quota_type()
            if len(quota_list) > 0:
                reporting.add_test_step("List Quota types", tvaultconf.PASS)
            else:
                raise exception("List Quota types")
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_03_workload_quota(self):
        reporting.add_test_script(str(__name__) + "_workload_quota")
        try:
            self.project_id = CONF.identity.tenant_id
            self.quota_type_id = self.get_quota_type_id(quota_type='Workloads')
            self.quota_id = self.create_project_quota(self.project_id, 
                    self.quota_type_id, tvaultconf.workload_allowed_value,
                    tvaultconf.workload_watermark_value)
            if self.quota_id:
                reporting.add_test_step("Create workload quota for project", tvaultconf.PASS)
            else:
                raise exception("Create workload quota for project")
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()
