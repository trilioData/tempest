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

LOG = logging.getLogger(__name__)
CONF = config.CONF

class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
	reporting.add_test_script(str(__name__))

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_tvault_rbac_nonadmin_notableto(self):
	try:
	    # Use non-admin credentials
	    os.environ['OS_USERNAME']= CONF.identity.nonadmin_user 
            os.environ['OS_PASSWORD']= CONF.identity.nonadmin_password

	    # Run get_storage_usage CLI
	    get_storage_usage  = command_argument_string.get_storage_usage
            LOG.debug("get_storage_usage  command: " + str(get_storage_usage))
            rc = cli_parser.cli_returncode(get_storage_usage)
            if rc != 0:
                reporting.add_test_step("Can not execute get_storage_usage command ", tvaultconf.PASS)
                LOG.debug("Command  get_storage_usage did not execute correctly")
            else:
                reporting.add_test_step("Can not execute get_storage_usage command", tvaultconf.FAIL)
                raise Exception("Command get_storage_usage executed correctly")

	    # Run get_import_workloads_list CLI
            get_import_workloads_list  = command_argument_string.get_import_workloads_list
            LOG.debug("get_import_workloads_list command: " + str(get_import_workloads_list))
            rc = cli_parser.cli_returncode(get_import_workloads_list)
            if rc != 0:
                reporting.add_test_step("Can not execute get_import_workloads_list command ", tvaultconf.PASS)
                LOG.debug("Command get_import_workloads_list did not execute correctly")
            else:
                reporting.add_test_step("Can not execute get_import_workloads_list command", tvaultconf.FAIL)
                raise Exception("Command get_import_workloads_list executed correctly")

            # Run workload_disable_global_job_scheduler CLI
            workload_disable_global_job_scheduler = command_argument_string.workload_disable_global_job_scheduler
            LOG.debug("workload_disable_global_job_scheduler command: " + str(workload_disable_global_job_scheduler))
            rc = cli_parser.cli_returncode(get_import_workloads_list)
            if rc != 0:
                reporting.add_test_step("Can not execute workload_disable_global_job_scheduler command ", tvaultconf.PASS)
                LOG.debug("Command workload_disable_global_job_scheduler did not execute correctly")
            else:
                reporting.add_test_step("Can not execute workload_disable_global_job_scheduler command", tvaultconf.FAIL)
                raise Exception("Command workload_disable_global_job_scheduler executed correctly")

	    # Run workload_enable_global_job_scheduler CLI
            workload_enable_global_job_scheduler = command_argument_string.workload_enable_global_job_scheduler
            LOG.debug("workload_enable_global_job_scheduler command: " + str(workload_enable_global_job_scheduler))
            rc = cli_parser.cli_returncode(workload_enable_global_job_scheduler)
            if rc != 0:
                reporting.add_test_step("Can not execute workload_enable_global_job_scheduler command ", tvaultconf.PASS)
                LOG.debug("Command workload_enable_global_job_scheduler did not execute correctly")
            else:
                reporting.add_test_step("Can not execute workload_enable_global_job_scheduler command", tvaultconf.FAIL)
                raise Exception("Command workload_enable_global_job_scheduler executed correctly")

            # Run get_nodes CLI
            get_nodes = command_argument_string.get_nodes
            LOG.debug("get_nodes command: " + str(get_nodes))
            rc = cli_parser.cli_returncode(get_nodes)
            if rc != 0:
                reporting.add_test_step("Can not execute get_nodes command ", tvaultconf.PASS)
                LOG.debug("Command get_nodes did not execute correctly")
            else:
                reporting.add_test_step("Can not execute get_nodes command", tvaultconf.FAIL)
                raise Exception("Command get_nodes executed correctly")

	    # Run license_check CLI
            license_check  = command_argument_string.license_check
            LOG.debug("license_check command: " + str(license_check))
            rc = cli_parser.cli_returncode(license_check)
            if rc != 0:
                reporting.add_test_step("Can not execute license_check command ", tvaultconf.PASS)
                LOG.debug("Command license_check did not execute correctly")
            else:
                reporting.add_test_step("Can not execute license_check command", tvaultconf.FAIL)
                raise Exception("Command license_check executed correctly")

	    # Run license_list CLI
	    license_list  = command_argument_string.license_list
            LOG.debug("license_list  command: " + str(license_list))
            rc = cli_parser.cli_returncode(license_list)
            if rc != 0:
                reporting.add_test_step("Can not execute license_list command ", tvaultconf.PASS)
                LOG.debug("Command  license_list did not execute correctly")
            else:
                reporting.add_test_step("Can not execute license_list command", tvaultconf.FAIL)
                raise Exception("Command  license_list executed correctly")

	    reporting.set_test_script_status(tvaultconf.PASS)
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
