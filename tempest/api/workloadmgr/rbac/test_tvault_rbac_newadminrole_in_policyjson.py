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
import time

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
    def test_tvault_rbac_newadminrole_in_policyjson(self):
	try:
	    # Change policy.json file on tvault to change role and rule
	    self.change_policyjson_file("newadmin", "newadmin_api")
	    	
	    # Use new-admin credentials
            os.environ['OS_USERNAME']= 'newadmin'
            os.environ['OS_PASSWORD']= 'password'

	    # Run get_storage_usage CLI by newadmin role
            get_storage_usage  = command_argument_string.get_storage_usage
            LOG.debug("get_storage_usage  command: " + str(get_storage_usage))
            rc = cli_parser.cli_returncode(get_storage_usage)
            if rc != 0:
                reporting.add_test_step("Execute get_storage_usage  command by newadmin role", tvaultconf.FAIL)
                raise Exception("Command  get_storage_usage did not execute correctly  by new-admin")
            else:
                reporting.add_test_step("Execute get_storage_usage command by new-admin role", tvaultconf.PASS)
                LOG.debug("Command get_storage_usage executed correctly by new-admin")

            # Run get_nodes CLI by newadmin role
            get_nodes = command_argument_string.get_nodes
            LOG.debug("get_nodes command: " + str(get_nodes))
            rc = cli_parser.cli_returncode(get_nodes)
            if rc != 0:
                reporting.add_test_step("Execute get_nodes command by newadmin role", tvaultconf.FAIL)
                raise Exception("Command get_nodes did not execute by new-admin")
            else:
                reporting.add_test_step("Execute get_nodes command by newadmin role", tvaultconf.PASS)
                LOG.debug("Command get_nodes executed correctly  by new-admin")


	    # Use admin credentials
            os.environ['OS_USERNAME']= 'admin'
            os.environ['OS_PASSWORD']= '065a81ab140f4f52'

            # Run get_storage_usage CLI by admin
            get_storage_usage  = command_argument_string.get_storage_usage
            LOG.debug("get_storage_usage  command: " + str(get_storage_usage))
            rc = cli_parser.cli_returncode(get_storage_usage)
            if rc != 0:
                reporting.add_test_step("Can not execute get_storage_usage command by admin role ", tvaultconf.PASS)
                LOG.debug("Command  get_storage_usage did not execute by admin role")
            else:
                reporting.add_test_step("Can not execute get_storage_usage command by admin role", tvaultconf.FAIL)
                raise Exception("Command get_storage_usage executed correctly by admin")

            # Run get_nodes CLI by admin
            get_nodes = command_argument_string.get_nodes
            LOG.debug("get_nodes command: " + str(get_nodes))
            rc = cli_parser.cli_returncode(get_nodes)
            if rc != 0:
                reporting.add_test_step("Can not execute get_nodes command by admin role", tvaultconf.PASS)
                LOG.debug("Command get_nodes did not execute by admin role")
            else:
                reporting.add_test_step("Can not execute get_nodes command by admin role", tvaultconf.FAIL)
                raise Exception("Command get_nodes executed correctly by admin")

	    # Use non-admin credentials
	    os.environ['OS_USERNAME']= 'nonadmin'
            os.environ['OS_PASSWORD']= 'password'

	    # Run get_storage_usage CLI by non-admin
	    get_storage_usage  = command_argument_string.get_storage_usage
            LOG.debug("get_storage_usage  command: " + str(get_storage_usage))
            rc = cli_parser.cli_returncode(get_storage_usage)
            if rc != 0:
                reporting.add_test_step("Can not execute get_storage_usage  command by non-admin", tvaultconf.PASS)
                LOG.debug("Command  get_storage_usage did not execute by nonadmin")
            else:
                reporting.add_test_step("Can not execute get_storage_usage command by non-admin", tvaultconf.FAIL)
                raise Exception("Command get_storage_usage executed by nonadmin")

            # Run get_nodes CLI by nonadmin
            get_nodes = command_argument_string.get_nodes
            LOG.debug("get_nodes command: " + str(get_nodes))
            rc = cli_parser.cli_returncode(get_nodes)
            if rc != 0:
                reporting.add_test_step("Can not execute get_nodes command by non-admin", tvaultconf.PASS)
                LOG.debug("Command get_nodes did not execute by nonadmin")
            else:
                reporting.add_test_step("Can not execute get_nodes command by non-admin", tvaultconf.FAIL)
                raise Exception("Command get_nodes executed by nonadmin")
	    
	    reporting.set_test_script_status(tvaultconf.PASS)
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

