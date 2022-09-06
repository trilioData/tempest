import os
import sys
import time

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
    vm_id = None
    vol_id = None

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    @decorators.attr(type='workloadmgr_cli')
    def test_01_create_workload_setting_with_required_param(self):
        reporting.add_test_script(str(__name__) + "_create_workload_setting_cli_with_required_param")
        try:
            # Create workload setting with CLI command
            wl_setting_create = command_argument_string.workload_setting_create + \
                              tvaultconf.workload_setting_name + " " + tvaultconf.workload_setting_value
            LOG.debug("Workload setting create command: {}".format(wl_setting_create))
            rc = cli_parser.cli_returncode(wl_setting_create)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload setting-create command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload setting-create command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            wc = query_data.get_created_workload_setting(tvaultconf.workload_setting_name)
            if (wc == tvaultconf.workload_setting_name):
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.PASS)
                LOG.debug(
                    "Workload setting-create command executed correctly")
            else:
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.FAIL)
                raise Exception(
                    "Workload setting-create command execution failed")
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_02_workload_setting_show(self):
        reporting.add_test_script(str(__name__) + "_workload_setting_show_cli")
        try:
            # workload setting show with CLI command
            wl_setting_show = command_argument_string.workload_setting_show + \
                              tvaultconf.workload_setting_name
            LOG.debug("Workload setting show command: {}".format(wl_setting_show))
            rc = cli_parser.cli_returncode(wl_setting_show)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload setting-show command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload setting-show command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            wc = query_data.get_created_workload_setting(tvaultconf.workload_setting_name)
            out = cli_parser.cli_output(wl_setting_show)
            LOG.debug("Response from CLI: " + str(out))

            if (wc == cli_parser.cli_response_parser(out, 'name')):
                reporting.add_test_step(
                    "Verify workload setting name", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload setting name", tvaultconf.FAIL)
            #if (wc == cli_parser.cli_response_parser(out, 'value')):
            #    reporting.add_test_step(
            #        "Verify workload setting value", tvaultconf.PASS)
            #else:
            #    reporting.add_test_step(
            #        "Verify workload setting value", tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_03_workload_setting_delete(self):
        reporting.add_test_script(str(__name__) + "_workload_setting_delete_cli")
        try:
            # workload setting delete with CLI command
            wl_setting_delete = command_argument_string.workload_setting_delete + \
                              tvaultconf.workload_setting_name
            LOG.debug("Workload setting delete command: {}".format(wl_setting_delete))
            rc = cli_parser.cli_returncode(wl_setting_delete)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload setting-delete command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload setting-delete command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            wc = query_data.get_created_workload_setting(tvaultconf.workload_setting_name)
            LOG.debug("Workload setting status: " + str(wc))
            if wc:
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.FAIL)
                raise Exception("Workload setting not deleted from DB")
            else:
                reporting.add_test_step(
                    "Workload setting deleted from DB", tvaultconf.PASS)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_04_create_workload_setting_with_optional_param(self):
        reporting.add_test_script(str(__name__) + "_create_workload_setting_cli_with_optional_param")
        try:
            # Create workload setting with CLI command
            wl_setting_create = command_argument_string.workload_setting_create + \
                              tvaultconf.workload_setting_name + " " + tvaultconf.workload_setting_value + \
                            " --description 'create-test' -- is-public True --is-hidden False" + \
                            " --metadata test_metadata=metadata_value1"
            LOG.debug("Workload setting create command: {}".format(wl_setting_create))
            rc = cli_parser.cli_returncode(wl_setting_create)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload setting-create command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload setting-create command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            wc = query_data.get_created_workload_setting(tvaultconf.workload_setting_name)
            if (wc == tvaultconf.workload_setting_name):
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.PASS)
                LOG.debug(
                    "Workload setting-create command executed correctly")
            else:
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.FAIL)
                raise Exception(
                    "Workload setting-create command execution failed")

            # Cleanup
            # Delete workload setting
            wl_setting_delete = command_argument_string.workload_setting_delete + \
                              tvaultconf.workload_setting_name
            LOG.debug("Workload setting delete command: {}".format(wl_setting_delete))
            wc = query_data.get_created_workload_setting(tvaultconf.workload_setting_name)
            LOG.debug("Workload setting status: " + str(wc))

            if wc:
                reporting.add_test_step(
                    "workload setting deletion failed", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "workload setting deleted successfully", tvaultconf.PASS)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_05_create_workload_setting_with_invalid_values(self):
        reporting.add_test_script(str(__name__) + "_create_workload_setting_cli_with_invalid_values")
        try:
            # Create workload setting with CLI command
            wl_setting_create = command_argument_string.workload_setting_create + \
                              tvaultconf.workload_setting_name
            LOG.debug("Workload setting create command with invalid values: {}".format(wl_setting_create))
            cli_err = cli_parser.cli_error(wl_setting_create)
            LOG.debug("cli error: {}".format(cli_err))
            if cli_err:
                reporting.add_test_step(
                    "Execute workload setting-create command with invalid values successful", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Execute workload setting-create command with invalid values failed", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

