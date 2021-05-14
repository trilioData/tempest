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


class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        reporting.add_test_script(str(__name__))

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    @decorators.attr(type='workloadmgr_cli')
    def test_tvault_rbac_newadminrole_in_policyjson(self):
        try:
            storage_usage_error_str = "Policy doesn't allow workload:get_storage_usage to be performed."
            get_nodes_error_str = "Policy doesn't allow workload:get_nodes to be performed."

            # Change policy.json file on tvault to change role and rule
            self.change_policyjson_file("newadmin", "newadmin_api")

            # Use new-admin credentials
            os.environ['OS_USERNAME'] = CONF.identity.newadmin_user
            os.environ['OS_PASSWORD'] = CONF.identity.newadmin_password

            # Run get_storage_usage CLI by newadmin role
            get_storage_usage = command_argument_string.get_storage_usage
            LOG.debug("get_storage_usage  command: " + str(get_storage_usage))
            error = cli_parser.cli_error(get_storage_usage)
            if error and (str(error.strip('\n')).find(storage_usage_error_str) != -1):
                reporting.add_test_step(
                    "Execute get_storage_usage command by newadmin role",
                    tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Execute get_storage_usage command by new-admin role",
                    tvaultconf.PASS)
                LOG.debug(
                    "Command get_storage_usage executed correctly by new-admin")

            # Run get_nodes CLI by newadmin role
            get_nodes = command_argument_string.get_nodes
            LOG.debug("get_nodes command: " + str(get_nodes))
            error = cli_parser.cli_error(get_nodes)
            if error and (str(error.strip('\n')).find(get_nodes_error_str) != -1):
                reporting.add_test_step(
                    "Execute get_nodes command by newadmin role",
                    tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Execute get_nodes command by newadmin role",
                    tvaultconf.PASS)
                LOG.debug("Command get_nodes executed correctly  by new-admin")

            # Use admin credentials
            os.environ['OS_USERNAME'] = CONF.identity.username
            os.environ['OS_PASSWORD'] = CONF.identity.password

            # Run get_storage_usage CLI by admin
            get_storage_usage = command_argument_string.get_storage_usage
            LOG.debug("get_storage_usage  command: " + str(get_storage_usage))
            error = cli_parser.cli_error(get_storage_usage)
            if error and (str(error.strip('\n')).find(storage_usage_error_str) != -1):
                reporting.add_test_step(
                    "Can not execute get_storage_usage command by admin role ",
                    tvaultconf.PASS)
                LOG.debug(
                    "Command  get_storage_usage did not execute by admin role")
            else:
                reporting.add_test_step(
                    "Can not execute get_storage_usage command by admin role",
                    tvaultconf.FAIL)

            # Run get_nodes CLI by admin
            get_nodes = command_argument_string.get_nodes
            LOG.debug("get_nodes command: " + str(get_nodes))
            error = cli_parser.cli_error(get_nodes)
            if error and (str(error.strip('\n')).find(get_nodes_error_str) != -1):
                reporting.add_test_step(
                    "Can not execute get_nodes command by admin role",
                    tvaultconf.PASS)
                LOG.debug("Command get_nodes did not execute by admin role")
            else:
                reporting.add_test_step(
                    "Can not execute get_nodes command by admin role",
                    tvaultconf.FAIL)

            # Use non-admin credentials
            os.environ['OS_USERNAME'] = CONF.identity.nonadmin_user
            os.environ['OS_PASSWORD'] = CONF.identity.nonadmin_password

            # Run get_storage_usage CLI by non-admin
            get_storage_usage = command_argument_string.get_storage_usage
            LOG.debug("get_storage_usage  command: " + str(get_storage_usage))
            error = cli_parser.cli_error(get_storage_usage)
            if error and (str(error.strip('\n')).find(storage_usage_error_str) != -1):
                reporting.add_test_step(
                    "Can not execute get_storage_usage  command by non-admin",
                    tvaultconf.PASS)
                LOG.debug(
                    "Command  get_storage_usage did not execute by nonadmin")
            else:
                reporting.add_test_step(
                    "Can not execute get_storage_usage command by non-admin",
                    tvaultconf.FAIL)

            # Run get_nodes CLI by nonadmin
            get_nodes = command_argument_string.get_nodes
            LOG.debug("get_nodes command: " + str(get_nodes))
            error = cli_parser.cli_error(get_nodes)
            if error and (str(error.strip('\n')).find(get_nodes_error_str) != -1):
                reporting.add_test_step(
                    "Can not execute get_nodes command by non-admin",
                    tvaultconf.PASS)
                LOG.debug("Command get_nodes did not execute by nonadmin")
            else:
                reporting.add_test_step(
                    "Can not execute get_nodes command by non-admin",
                    tvaultconf.FAIL)

            reporting.set_test_script_status(tvaultconf.PASS)
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
