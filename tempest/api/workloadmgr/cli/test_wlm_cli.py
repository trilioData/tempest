import os
import sys
import time
import random
import json
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
            if (wc[0] == tvaultconf.workload_setting_name):
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
            LOG.debug("DB query data: {}".format(wc))
            out = cli_parser.cli_output(wl_setting_show)
            LOG.debug("Response from CLI: " + str(out))

            if (wc[0] == cli_parser.cli_response_parser(out, 'name')):
                reporting.add_test_step(
                    "Verify workload setting name", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload setting name", tvaultconf.FAIL)
            if (wc[1] == cli_parser.cli_response_parser(out, 'value')):
                reporting.add_test_step(
                    "Verify workload setting value", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload setting value", tvaultconf.FAIL)

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
            workload_setting_name = tvaultconf.workload_setting_name + str(random.randint(0, 10000))
            text_metadata = "test_metadata=metadata_value1"
            # Create workload setting with CLI command
            wl_setting_create = command_argument_string.workload_setting_create + \
                                workload_setting_name + " " + tvaultconf.workload_setting_value + \
                                " --description 'create-test' --is-public True --is-hidden False" + \
                                " --category cat1 --type type1 --metadata " + text_metadata
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

            wc = query_data.get_created_workload_setting(workload_setting_name)
            LOG.debug("workload settings in db: {}".format(wc))
            if (wc[0] == workload_setting_name):
                reporting.add_test_step(
                    "Verification with DB for created workload-setting", tvaultconf.PASS)
                LOG.debug(
                    "Workload setting-create command executed correctly")
            else:
                reporting.add_test_step(
                    "Verification with DB for created workload-setting", tvaultconf.FAIL)
                raise Exception(
                    "Workload setting-create command execution failed")

            wl_setting_show = command_argument_string.workload_setting_show + workload_setting_name
            out = cli_parser.cli_output(wl_setting_show)
            LOG.debug("Response from CLI: " + str(out))
            if (wc[0] == cli_parser.cli_response_parser(out, 'name')):
                reporting.add_test_step(
                    "Verify workload setting name", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload setting name", tvaultconf.FAIL)
            if (wc[1] == cli_parser.cli_response_parser(out, 'value')):
                reporting.add_test_step(
                    "Verify workload setting value", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload setting value", tvaultconf.FAIL)
            if (wc[2] == cli_parser.cli_response_parser(out, 'description')):
                reporting.add_test_step(
                    "Verify workload setting description", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload setting description", tvaultconf.FAIL)
            if (wc[3] == cli_parser.cli_response_parser(out, 'category')):
                reporting.add_test_step(
                    "Verify workload setting category", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload setting category", tvaultconf.FAIL)
            if (wc[4] == cli_parser.cli_response_parser(out, 'type')):
                reporting.add_test_step(
                    "Verify workload setting type", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload setting type", tvaultconf.FAIL)
            if ("test_metadata" in cli_parser.cli_response_parser(out, 'metadata')):
                reporting.add_test_step(
                    "Verify workload setting metadata", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload setting metadata", tvaultconf.FAIL)

                # Cleanup
            # Delete workload setting
            wl_setting_delete = command_argument_string.workload_setting_delete + \
                                workload_setting_name
            LOG.debug("Workload setting delete command: {}".format(wl_setting_delete))
            rc = cli_parser.cli_returncode(wl_setting_delete)
            time.sleep(10)
            wc = query_data.get_created_workload_setting(workload_setting_name)
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
            cli_error_string = tvaultconf.wl_setting_cli_error_string
            # Create workload setting with CLI command
            wl_setting_name = tvaultconf.workload_setting_name + str(random.randint(0, 10000))
            wl_setting_create = command_argument_string.workload_setting_create + " " + wl_setting_name
            LOG.debug("Workload setting create command with invalid values: {}".format(wl_setting_create))
            rc = cli_parser.cli_returncode(wl_setting_create)
            if rc == 0:
                reporting.add_test_step(
                    "Execute workload setting-create with invalid values", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload setting-create with invalid values", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            cli_err = cli_parser.cli_error(wl_setting_create)
            LOG.debug("cli error: {}".format(cli_err))
            if (cli_err and cli_error_string in cli_err):
                reporting.add_test_step(
                    "Verify error thrown for invalid parameter", tvaultconf.PASS)
                LOG.debug("Command executed correctly")
            else:
                reporting.add_test_step(
                    "Verify error thrown for invalid parameter", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_06_workload_setting_update(self):
        reporting.add_test_script(str(__name__) + "_update_workload_setting_cli")
        try:
            # Create workload setting with CLI command
            global workload_setting_name
            workload_setting_name = tvaultconf.workload_setting_name + str(random.randint(0, 10000))
            wl_setting_create = command_argument_string.workload_setting_create + \
                                workload_setting_name + " " + tvaultconf.workload_setting_value + \
                                " --is-hidden True"
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

            # workload setting show with CLI command
            wl_setting_show = command_argument_string.workload_setting_show + \
                              workload_setting_name + " --get_hidden True"
            LOG.debug("workloadmgr setting-show command: {}".format(wl_setting_show))
            out = cli_parser.cli_output(wl_setting_show)
            LOG.debug("Response from CLI: " + str(out))

            if (workload_setting_name == cli_parser.cli_response_parser(out, 'name')):
                reporting.add_test_step(
                    "Verify workload setting name", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload setting name", tvaultconf.FAIL)
            if (tvaultconf.workload_setting_value == cli_parser.cli_response_parser(out, 'value')):
                reporting.add_test_step(
                    "Verify workload setting value", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload setting value", tvaultconf.FAIL)
            if (cli_parser.cli_response_parser(out, 'hidden') == 'True'):
                reporting.add_test_step(
                    "Verify workload setting get-hidden", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload setting get-hidden", tvaultconf.FAIL)

            update_val = "value123"
            # workload setting update with CLI command
            wl_setting_update = command_argument_string.workload_setting_update + \
                                workload_setting_name + " " + update_val + " --is-hidden False"

            rc = cli_parser.cli_returncode(wl_setting_update)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload setting-update command", tvaultconf.FAIL)
                raise Exception("workload setting-update command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload setting-update command", tvaultconf.PASS)
                LOG.debug("workload setting-update command executed correctly")

            # Compare values after updating workloadmgr setting
            wc = query_data.get_created_workload_setting(workload_setting_name)
            LOG.debug("workload settings in db: {}".format(wc))

            wl_setting_show = command_argument_string.workload_setting_show + workload_setting_name
            out = cli_parser.cli_output(wl_setting_show)
            LOG.debug("Response from CLI: " + str(out))
            if (wc[0] == cli_parser.cli_response_parser(out, 'name')):
                reporting.add_test_step(
                    "Verify workload setting name after updation", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload setting name after updation", tvaultconf.FAIL)
            if (cli_parser.cli_response_parser(out, 'value') == update_val):
                reporting.add_test_step(
                    "Verify workload setting value after updation", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload setting value after updation", tvaultconf.FAIL)
            if (cli_parser.cli_response_parser(out, 'hidden') == 'False'):
                reporting.add_test_step(
                    "Verify workload setting get-hidden after updation", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload setting get-hidden after updation", tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_07_update_workload_setting_with_invalid_values(self):
        reporting.add_test_script(str(__name__) + "_update_workload_setting_cli_with_invalid_values")
        try:
            cli_error_string = tvaultconf.wl_setting_update_cli_error_string
            wl_setting_update = command_argument_string.workload_setting_update + " " + workload_setting_name + \
                                " value45 --description --type set2"
            LOG.debug("Workload setting update command with invalid values: {}".format(wl_setting_update))
            rc = cli_parser.cli_returncode(wl_setting_update)
            if rc == 0:
                reporting.add_test_step(
                    "Execute workload setting-update with invalid values", tvaultconf.FAIL)
                raise Exception("workload setting-update command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload setting-update with invalid values", tvaultconf.PASS)
                LOG.debug("workload setting-update command executed correctly")

            cli_err = cli_parser.cli_error(wl_setting_update)
            LOG.debug("cli error: {}".format(cli_err))
            if (cli_err and cli_error_string in cli_err):
                reporting.add_test_step(
                    "Verify correct error thrown for invalid parameter", tvaultconf.PASS)
                LOG.debug("Command executed correctly")
            else:
                reporting.add_test_step(
                    "Verify correct error thrown for invalid parameter", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # Cleanup
            # Delete workload setting
            wl_setting_delete = command_argument_string.workload_setting_delete + \
                                workload_setting_name
            LOG.debug("Workload setting delete command: {}".format(wl_setting_delete))
            rc = cli_parser.cli_returncode(wl_setting_delete)
            time.sleep(10)
            wc = query_data.get_created_workload_setting(workload_setting_name)
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
    def test_08_workload_setting_list(self):
        reporting.add_test_script(str(__name__) + "_create_workload_setting_cli_list")
        try:
            # workload setting list with CLI command
            wl_setting_list = command_argument_string.workload_setting_list + " --get_hidden True -f value | wc -l"
            LOG.debug("Workload setting list command: {}".format(wl_setting_list))
            rc = cli_parser.cli_returncode(wl_setting_list)
            if rc == 0:
                reporting.add_test_step(
                    "Execute workload setting-list", tvaultconf.PASS)
                LOG.debug("workload setting-list command executed correctly")
            else:
                reporting.add_test_step(
                    "Execute workload setting-list", tvaultconf.FAIL)
                raise Exception("workload setting-list command did not execute correctly")

            out = cli_parser.cli_output(wl_setting_list)
            LOG.debug("Response from CLI: " + str(out))

            # Compare values with database for workloadmgr setting-list
            wc = query_data.get_db_rows_count("settings", "hidden", str(1))
            LOG.debug("workload settings in db: {}".format(wc))
            if (wc == int(out) - 4) or (wc == int(out)):
                reporting.add_test_step(
                    "Verify workload setting list with DB", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload setting list with DB", tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_09_list_workload_setting_with_invalid_values(self):
        reporting.add_test_script(str(__name__) + "_list_workload_setting_cli_with_invalid_values")
        try:
            cli_error_string = tvaultconf.wl_setting_list_cli_error_string
            wl_setting_list = command_argument_string.workload_setting_list + " --get_hidden"
            LOG.debug("Workload setting list command with invalid values: {}".format(wl_setting_list))
            rc = cli_parser.cli_returncode(wl_setting_list)
            if rc == 0:
                reporting.add_test_step(
                    "Execute workload setting-list with invalid values", tvaultconf.FAIL)
                raise Exception("workload setting-list command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload setting-list with invalid values", tvaultconf.PASS)
                LOG.debug("workload setting-list command executed correctly")

            cli_err = cli_parser.cli_error(wl_setting_list)
            LOG.debug("cli error: {}".format(cli_err))
            if (cli_err and cli_error_string in cli_err):
                reporting.add_test_step(
                    "Verify error thrown for invalid parameter", tvaultconf.PASS)
                LOG.debug("Command executed correctly")
            else:
                reporting.add_test_step(
                    "Verify error thrown for invalid parameter", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_10_token(self):
        reporting.add_test_script(str(__name__) + "_token")
        try:
            os.environ.pop('OS_USERNAME', None)
            os.environ.pop('OS_PASSWORD', None)
            env_vars = os.environ
            LOG.debug(f"Environment variables: {env_vars}")
            os_token = self.get_os_token()
            LOG.debug(f"Token created: {os_token}")
            os.environ['OS_AUTH_TYPE'] = 'token'
            os.environ['OS_TOKEN'] = os_token
            os.environ.pop('OS_USER_DOMAIN_NAME', None)

            rc = cli_parser.cli_returncode(
                    command_argument_string.workload_list)
            if rc == 0:
                reporting.add_test_step(
                    "Execute WLM cli command for workload-list", 
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Execute WLM cli command for workload-list", 
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            rc = cli_parser.cli_returncode(
                    command_argument_string.os_server_list)
            if rc == 0:
                reporting.add_test_step(
                    "Execute OpenStack cli command for server list",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Execute OpenStack cli command for server list",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            rc = cli_parser.cli_returncode(
                    command_argument_string.os_workload_list)
            if rc == 0:
                reporting.add_test_step(
                    "Execute OpenStack cli command for workload-list", 
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Execute OpenStack cli command for workload-list", 
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_11_get_tenants_usage(self):
        reporting.add_test_script(str(__name__) + "_get_tenants_usage_cli")
        try:
            
            self.vm_id = self.create_vm()
                  
            # Create workload with CLI command
            workload_create = command_argument_string.workload_create + \
                " instance-id=" + str(self.vm_id)
            rc = cli_parser.cli_returncode(workload_create)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-create command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-create command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")
            time.sleep(10)
             
            # List VMs 
            vm_list = self.list_vms()
            LOG.debug("\nVM lists are : {}\n".format(str(vm_list)))

            #Fetch protected VMs : First We need to fetch the instances from WL list and then remove them who are not in the vm_list so WL VMs who are deleted from OpenStack but they still part of WL will get excluded
            wl_list = self.getWorkloadList()
            LOG.debug("\nWL lists are : {}\n".format(str(wl_list)))
            wl_instance_id = []
            for workload in wl_list:
                body = self.getWorkloadDetails(workload)
                LOG.debug("Body from WorkloadDetails:" + str(body))
                for count in range(0, len(body['instances'])):
                    wl_instance_id.append(body['instances'][count]['id'])
                LOG.debug("\nWL instances are: " +str(wl_instance_id))

            protected_vm_list = []
            for vm in wl_instance_id:
                if vm in vm_list:
                    protected_vm_list.append(vm)
            LOG.debug("\nProtected VMs are: " +str(protected_vm_list))

            # Get tenant usage CLI command
            get_tenant_usage = command_argument_string.get_tenant_usage
            LOG.debug("Get tenant usage command: {}".format(get_tenant_usage))
            rc = cli_parser.cli_returncode(get_tenant_usage)
            if rc != 0:
                reporting.add_test_step(
                    "Execute get-tenants-usage command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute get-tenants-usage command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")
            
            # Compare total VMs hosted on a cloud vs total_vms showing in CLI output
            out = cli_parser.cli_output(get_tenant_usage)
            total_vm = cli_parser.cli_response_parser(out,'total_vms')
            if (len(vm_list) == int(total_vm)):
                reporting.add_test_step(
                    "Verify total VMs on OpenStack and CLI ouput", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify total VMs on OpenStack and CLI ouput", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            
            # Compare the vms_protected vs CLI ouput
            usage = cli_parser.cli_response_parser(out, CONF.identity.tenant_name)
            protected_vm = json.loads(usage)
            if int(protected_vm['vms_protected']) == len(protected_vm_list):
                reporting.add_test_step(
                    "Verify VMs_protected vs CLI ouput", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify VMs_protected vs CLI ouput", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            
            # Delete workload
            self.workload_delete(self.wid)
            LOG.debug("Workload deleted successfully")
            
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()
