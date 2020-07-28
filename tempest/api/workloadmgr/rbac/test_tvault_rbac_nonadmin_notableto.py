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


class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        reporting.add_test_script(str(__name__))

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_tvault_rbac_nonadmin_notableto(self):
        try:
            storage_usage_error_str = "Policy doesn't allow workload:get_storage_usage to be performed."
            import_workload_list_error_str = "Policy doesn't allow workload:get_import_workloads_list to be performed."
            disable_job_sch_error_str = "Policy doesn't allow workload:workload_disable_global_job_scheduler to be performed."
            enable_job_sch_error_str = "Policy doesn't allow workload:workload_enable_global_job_scheduler to be performed."
            get_nodes_error_str = "Policy doesn't allow workload:get_nodes to be performed."
            license_check_error_str = "Policy doesn't allow workload:license_check to be performed."
            license_list_error_str = "Policy doesn't allow workload:license_list to be performed."

            # Use non-admin credentials
            os.environ['OS_USERNAME'] = CONF.identity.nonadmin_user
            os.environ['OS_PASSWORD'] = CONF.identity.nonadmin_password

            # Run get_storage_usage CLI
            get_storage_usage = command_argument_string.get_storage_usage
            LOG.debug("get_storage_usage  command: " + str(get_storage_usage))
            error = cli_parser.cli_error(get_storage_usage)
            if error and (str(error.strip('\n')).find(storage_usage_error_str) != -1):
                reporting.add_test_step(
                    "Can not execute get_storage_usage command ",
                    tvaultconf.PASS)
                LOG.debug("Command get_storage_usage did not execute correctly")
            else:
                reporting.add_test_step(
                    "Can not execute get_storage_usage command",
                    tvaultconf.FAIL)

            # Run get_import_workloads_list CLI
            get_import_workloads_list = command_argument_string.get_import_workloads_list
            LOG.debug("get_import_workloads_list command: " +
                      str(get_import_workloads_list))
            error = cli_parser.cli_error(get_import_workloads_list)
            if error and (str(error.strip('\n')).find(import_workload_list_error_str) != -1):
                reporting.add_test_step(
                    "Can not execute get_import_workloads_list command ",
                    tvaultconf.PASS)
                LOG.debug(
                    "Command get_import_workloads_list did not execute correctly")
            else:
                reporting.add_test_step(
                    "Can not execute get_import_workloads_list command",
                    tvaultconf.FAIL)

            # Run workload_disable_global_job_scheduler CLI
            workload_disable_global_job_scheduler = command_argument_string.workload_disable_global_job_scheduler
            LOG.debug("workload_disable_global_job_scheduler command: " +
                      str(workload_disable_global_job_scheduler))
            error = cli_parser.cli_error(workload_disable_global_job_scheduler)
            if error and (str(error.strip('\n')).find(disable_job_sch_error_str) != -1):
                reporting.add_test_step(
                    "Can not execute workload_disable_global_job_scheduler command ",
                    tvaultconf.PASS)
                LOG.debug(
                    "Command workload_disable_global_job_scheduler did not execute correctly")
            else:
                reporting.add_test_step(
                    "Can not execute workload_disable_global_job_scheduler command",
                    tvaultconf.FAIL)

            # Run workload_enable_global_job_scheduler CLI
            workload_enable_global_job_scheduler = command_argument_string.workload_enable_global_job_scheduler
            LOG.debug("workload_enable_global_job_scheduler command: " +
                      str(workload_enable_global_job_scheduler))
            error = cli_parser.cli_error(workload_enable_global_job_scheduler)
            if error and (str(error.strip('\n')).find(enable_job_sch_error_str) != -1):
                reporting.add_test_step(
                    "Can not execute workload_enable_global_job_scheduler command ",
                    tvaultconf.PASS)
                LOG.debug(
                    "Command workload_enable_global_job_scheduler did not execute correctly")
            else:
                reporting.add_test_step(
                    "Can not execute workload_enable_global_job_scheduler command",
                    tvaultconf.FAIL)

            # Run get_nodes CLI
            get_nodes = command_argument_string.get_nodes
            LOG.debug("get_nodes command: " + str(get_nodes))
            error = cli_parser.cli_error(get_nodes)
            if error and (str(error.strip('\n')).find(get_nodes_error_str) != -1):
                reporting.add_test_step(
                    "Can not execute get_nodes command ", tvaultconf.PASS)
                LOG.debug("Command get_nodes did not execute correctly")
            else:
                reporting.add_test_step(
                    "Can not execute get_nodes command", tvaultconf.FAIL)

            # Run license_check CLI
            license_check = command_argument_string.license_check
            LOG.debug("license_check command: " + str(license_check))
            error = cli_parser.cli_error(license_check)
            if error and (str(error.strip('\n')).find(license_check_error_str) != -1):
                reporting.add_test_step(
                    "Can not execute license_check command ", tvaultconf.PASS)
                LOG.debug("Command license_check did not execute correctly")
            else:
                reporting.add_test_step(
                    "Can not execute license_check command", tvaultconf.FAIL)

            # Run license_list CLI
            license_list = command_argument_string.license_list
            LOG.debug("license_list  command: " + str(license_list))
            error = cli_parser.cli_error(license_list)
            if error and (str(error.strip('\n')).find(license_list_error_str) != -1):
                reporting.add_test_step(
                    "Can not execute license_list command ", tvaultconf.PASS)
                LOG.debug("Command  license_list did not execute correctly")
            else:
                reporting.add_test_step(
                    "Can not execute license_list command", tvaultconf.FAIL)

            reporting.set_test_script_status(tvaultconf.PASS)
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
