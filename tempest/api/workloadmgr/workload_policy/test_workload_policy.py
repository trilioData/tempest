import os
import sys
import time

from oslo_log import log as logging

from tempest import command_argument_string
from tempest import config
from tempest import reporting
from tempest import test
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
    wid = ""
    vm_id = ""
    volume_id = ""
    policy_id = ""

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    @decorators.attr(type='workloadmgr_cli')
    def test_1_workload_policy_create(self):
        reporting.add_test_script(str(__name__) + "_create")
        try:
            global policy_id
            policy_create_error_str = "Policy doesn't allow workload:policy_create to be performed."

            # Create workload policy by admin user
            policy_id = self.workload_policy_create(
                interval=tvaultconf.interval, policy_cleanup=False)
            if policy_id != "":
                reporting.add_test_step(
                    "Create workload policy by admin user", tvaultconf.PASS)
                LOG.debug("Workload policy id is " + str(policy_id))
            else:
                reporting.add_test_step(
                    "Create workload policy by admin user", tvaultconf.FAIL)
                raise Exception(
                    "Workload policy has not been created by admin user")

            # Verify policy is created by admin user
            policy_list = self.get_policy_list()
            if policy_id in policy_list:
                reporting.add_test_step(
                    "Verify policy created by admin user", tvaultconf.PASS)
                LOG.debug("Policy is created by admin user")
            else:
                reporting.add_test_step(
                    "Verify policy created by admin user", tvaultconf.FAIL)
                raise Exception("Policy is not created by admin user")

            # Use non-admin credentials
            os.environ['OS_USERNAME'] = CONF.identity.nonadmin_user
            os.environ['OS_PASSWORD'] = CONF.identity.nonadmin_password

            # Create workload policy by nonadmin user using CLI
            policy_create_command = command_argument_string.policy_create + "interval='" + tvaultconf.interval + "' --policy-fields retention_policy_type='"\
                + tvaultconf.retention_policy_type + "' --policy-fields retention_policy_value='" + tvaultconf.retention_policy_value + \
                "' --policy-fields fullbackup_interval='" + \
                tvaultconf.fullbackup_interval + "' nonadmin_policy"
            LOG.debug("policy_create_command#### " + policy_create_command)
            error = cli_parser.cli_error(policy_create_command)
            if error and (str(error.strip('\n')).find(policy_create_error_str) != -1):
                reporting.add_test_step(
                    "Can not create workload policy by nonadmin user",
                    tvaultconf.PASS)
                LOG.debug("Policy is not created by nonadmin user")
            else:
                reporting.add_test_step(
                    "Can not create workload policy by nonadmin user",
                    tvaultconf.FAIL)
                raise Exception("Policy is created by nonadmin user")
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_2_workload_policy_update(self):
        reporting.add_test_script(str(__name__) + "_update")
        try:
            global policy_id
            policy_update_error_str = "Policy doesn't allow workload:policy_update to be performed."

            # Update workload policy by admin user
            updated_status = self.workload_policy_update(
                policy_id,
                policy_name=tvaultconf.policy_name_update,
                fullbackup_interval=tvaultconf.fullbackup_interval_update,
                interval=tvaultconf.interval_update,
                retention_policy_value=tvaultconf.retention_policy_value_update)
            if updated_status:
                reporting.add_test_step(
                    "Update workload policy by admin user", tvaultconf.PASS)
                LOG.debug("Workload policy has been updated by admin user")
            else:
                reporting.add_test_step(
                    "Update workload policy by admin user", tvaultconf.FAIL)
                raise Exception("Workload policy not updated by admin user")

            # Verify workload policy updated parameters
            # Below function returns list as [policy_name, {field_values},
            # policy_id, description, [list_of_project_assigned]]
            details = self.get_policy_details(policy_id)
            if not details:
                reporting.add_test_step(
                    "Verify workload policy parameters updated",
                    tvaultconf.FAIL)
                raise Exception("Workload policy not updated")
            else:
                if tvaultconf.policy_name_update == details[0] and tvaultconf.interval_update == details[1]['interval'] and tvaultconf.retention_policy_value_update ==\
                   details[1]['retention_policy_value'] and tvaultconf.fullbackup_interval_update == details[1]['fullbackup_interval']:
                    reporting.add_test_step(
                        "Verify workload policy parameters updated", tvaultconf.PASS)
                    LOG.debug("Policy updated successfully")
                else:
                    reporting.add_test_step(
                        "Verify workload policy parameters updated", tvaultconf.FAIL)
                    raise Exception("Workload policy updated incorrect")

            # Use non-admin credentials
            os.environ['OS_USERNAME'] = CONF.identity.nonadmin_user
            os.environ['OS_PASSWORD'] = CONF.identity.nonadmin_password

            # Update workload policy by nonadmin user using CLI
            policy_update_command = command_argument_string.policy_update + "interval='" + tvaultconf.interval_update + "' --policy-fields retention_policy_value='" +\
                tvaultconf.retention_policy_value_update + "' --policy-fields fullbackup_interval='" + tvaultconf.fullbackup_interval_update + \
                "' --display-name 'policy_update' " + str(policy_id)
            error = cli_parser.cli_error(policy_update_command)
            if error and (str(error.strip('\n')).find(policy_update_error_str) != -1):
                reporting.add_test_step(
                    "Can not update workload policy by nonadmin user",
                    tvaultconf.PASS)
                LOG.debug("Policy is not updated by nonadmin user")
            else:
                reporting.add_test_step(
                    "Can not update workload policy by nonadmin user",
                    tvaultconf.FAIL)
                raise Exception("Policy is updated by nonadmin user")
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_3_workload_policy_assign(self):
        reporting.add_test_script(str(__name__) + "_assign")
        try:
            global policy_id
            policy_assign_error_str = "User does not have admin privileges"

            # Assign workload policy to projects by admin user
            admin_project_id = CONF.identity.admin_tenant_id
            status = self.assign_unassign_workload_policy(
                policy_id, add_project_ids_list=[admin_project_id], remove_project_ids_list=[])
            if status:
                reporting.add_test_step(
                    "Assign workload policy by admin user", tvaultconf.PASS)
                LOG.debug("Workload policy is assigned to project by admin user")
            else:
                reporting.add_test_step(
                    "Assign workload policy by admin user", tvaultconf.FAIL)
                raise Exception(
                    "Workload policy not assigned to project by admin user")

            # Verify policy assigned to tenant by admin user
            details = self.get_policy_details(policy_id)
            if admin_project_id in details[4]:
                reporting.add_test_step(
                    "Verify policy assigned by admin user", tvaultconf.PASS)
                LOG.debug(
                    "Workload policy is assigned to project by admin user successfully")
            else:
                reporting.add_test_step(
                    "Verify policy assigned by admin user", tvaultconf.FAIL)
                raise Exception(
                    "Workload policy not assigned to project by admin user unsuccessfully")

            # Verify policy assigned to tenant by admin user using list_assigned_policies cli
            cmd = command_argument_string.list_assigned_policies + admin_project_id + " -f value"
            rc = cli_parser.cli_returncode(cmd)
            if rc != 0:
                reporting.add_test_step(
                    "Execute list_assigned_policies command is successful",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Execute list_assigned_policies command is successful",
                    tvaultconf.PASS)

            LOG.debug("cli command: {}".format(cmd))
            out = cli_parser.cli_output(cmd)
            LOG.debug("Response from CLI: " + str(out))
            if (policy_id in out):
                reporting.add_test_step(
                    "Verify list_assigned_policy shows assigned project_id", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify list_assigned_policy shows assigned project_id", tvaultconf.FAIL)

            # Update workload policy which is assigned to tenant
            updated_status = self.workload_policy_update(
                policy_id,
                policy_name=tvaultconf.policy_name_update,
                fullbackup_interval=tvaultconf.fullbackup_interval_update,
                interval=tvaultconf.interval_update,
                retention_policy_value=tvaultconf.retention_policy_value_update)
            if updated_status:
                reporting.add_test_step(
                    "Update workload policy which is assigned to tenant",
                    tvaultconf.PASS)
                LOG.debug("Assigned workload policy has been updated")
            else:
                reporting.add_test_step(
                    "Update workload policy which is assigned to tenantr",
                    tvaultconf.FAIL)
                raise Exception(
                    "Assigned workload policy not updated by admin user")

            # DB validations for workload policy before
            workload_policy_validations_before = self.db_cleanup_workload_policy_validations(policy_id)
            LOG.debug("Workload policy table values before deletion: {}".format(workload_policy_validations_before))

            # Verify workload policy which has assigned to tenant is updated with parameters
            # Below function returns list as [policy_name, {field_values},
            # policy_id, description, [list_of_project_assigned]]
            details = self.get_policy_details(policy_id)
            if not details:
                reporting.add_test_step(
                    "Verify workload policy parameters updated",
                    tvaultconf.FAIL)
                raise Exception("Workload policy not updated")
            else:
                if tvaultconf.policy_name_update == details[0] and tvaultconf.interval_update == details[1]['interval'] and tvaultconf.retention_policy_value_update ==\
                    details[1]['retention_policy_value'] and tvaultconf.fullbackup_interval_update == details[1]['fullbackup_interval']:
                    reporting.add_test_step(
                        "Verify workload policy parameters updated", tvaultconf.PASS)
                    LOG.debug("Policy updated successfully")
                else:
                    reporting.add_test_step(
                        "Verify workload policy parameters updated", tvaultconf.FAIL)
                    raise Exception("Workload policy updated incorrect")

            # Deassign workload policy to projects by admin user
            status = self.assign_unassign_workload_policy(
                policy_id, add_project_ids_list=[], remove_project_ids_list=[admin_project_id])
            if status:
                reporting.add_test_step(
                    "Unassign workload policy by admin user", tvaultconf.PASS)
                LOG.debug("Workload policy is unassigned by admin user")
            else:
                reporting.add_test_step(
                    "Unassign workload policy by admin user", tvaultconf.FAIL)
                raise Exception("Workload policy not Unassigned by admin user")

            # Verify policy unassigned to tenant by admin user
            details = self.get_policy_details(policy_id)
            if admin_project_id not in details[4]:
                reporting.add_test_step(
                    "Verify policy unassigned by admin user", tvaultconf.PASS)
                LOG.debug(
                    "Workload policy is unassigned by admin user successfully")
            else:
                reporting.add_test_step(
                    "Verify policy unassigned by admin user", tvaultconf.FAIL)
                raise Exception(
                    "Workload policy not unassigned by admin user unsuccessfully")

            # Verify unassigned policy is not listed in list_assigned_policies cli
            cmd = command_argument_string.list_assigned_policies + admin_project_id
            rc = cli_parser.cli_returncode(cmd)
            LOG.debug("Response from CLI: " + str(rc))
            if rc != 0:
                reporting.add_test_step(
                    "Execute list_assigned_policies command is successful",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Execute list_assigned_policies command is successful",
                    tvaultconf.PASS)

            LOG.debug("cli command: {}".format(cmd))
            out = cli_parser.cli_output(cmd)
            LOG.debug("Response from CLI: " + str(out))
            if (policy_id not in out):
                reporting.add_test_step(
                    "Verify list_assigned_policy does not show assigned project_id", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify list_assigned_policy does not show assigned project_id", tvaultconf.FAIL)

            # Use non-admin credentials
            os.environ['OS_USERNAME'] = CONF.identity.nonadmin_user
            os.environ['OS_PASSWORD'] = CONF.identity.nonadmin_password

            # Assign workload policy to tenant by nonadmin user using CLI
            project_id = CONF.identity.tenant_id
            policy_assign_command = command_argument_string.policy_assign + \
                str(project_id) + " " + str(policy_id)
            error = cli_parser.cli_error(policy_assign_command)
            if error and (str(error.strip('\n')).find(policy_assign_error_str) != -1):
                reporting.add_test_step(
                    "Cannot assign workload policy by nonadmin user",
                    tvaultconf.PASS)
                LOG.debug("Policy is not assigned by nonadmin user")
            else:
                reporting.add_test_step(
                    "Cannot assign workload policy by nonadmin user",
                    tvaultconf.FAIL)
                raise Exception("Policy is assigned by nonadmin user")
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_4_list_assigned_policies(self):
        reporting.add_test_script(str(__name__) + "_list_assigned_policies")
        try:
            global policy_id
            cli_error_string = tvaultconf.wl_assigned_policy_error_string
            cli_error_string_noprojectid = tvaultconf.wl_assigned_policy_no_projectid_error_string
            # Assign workload policy to projects by admin user
            admin_project_id = CONF.identity.admin_tenant_id
            status = self.assign_unassign_workload_policy(
                policy_id, add_project_ids_list=[admin_project_id], remove_project_ids_list=[])
            if status:
                reporting.add_test_step(
                    "Assign workload policy by admin user", tvaultconf.PASS)
                LOG.debug("Workload policy is assigned to project by admin user")
            else:
                reporting.add_test_step(
                    "Assign workload policy by admin user", tvaultconf.FAIL)
                raise Exception(
                    "Workload policy not assigned to project by admin user")

            # Verify policy assigned to tenant by admin user using list_assigned_policies cli
            cmd = command_argument_string.list_assigned_policies
            rc = cli_parser.cli_returncode(cmd)
            if rc != 0:
                reporting.add_test_step(
                    "Execute list_assigned_policies command with no project_id is successful",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Execute list_assigned_policies command with no project_id is not successful",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            cli_err = cli_parser.cli_error(cmd)
            LOG.debug("cli error: {}".format(cli_err))
            if (cli_err and cli_error_string_noprojectid in cli_err):
                reporting.add_test_step(
                    "Verify list_assigned_policy throws proper error", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify list_assigned_policy throws proper error", tvaultconf.FAIL)

            # Verify policy assigned to tenant by admin user using list_assigned_policies cli
            cmd = command_argument_string.list_assigned_policies + admin_project_id + " -c id"
            rc = cli_parser.cli_returncode(cmd)
            if rc == 0:
                reporting.add_test_step(
                    "Execute list_assigned_policies command with incorrect column is successful",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Execute list_assigned_policies command with incorrect column is not successful",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            cli_err = cli_parser.cli_error(cmd)
            LOG.debug("cli error: {}".format(cli_err))
            if (cli_err and cli_error_string in cli_err):
                reporting.add_test_step(
                    "Verify list_assigned_policy command with incorrect column throws proper error", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify list_assigned_policy command with incorrect column throws proper error", tvaultconf.FAIL)

            # Verify policy assigned to tenant by admin user using list_assigned_policies cli
            cmd = command_argument_string.list_assigned_policies + admin_project_id + " -c ID -f value"
            LOG.debug("cli command: {}".format(cmd))
            rc = cli_parser.cli_returncode(cmd)
            if rc != 0:
                reporting.add_test_step(
                    "Execute list_assigned_policies command with column 'ID' is successful",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Execute list_assigned_policies command with column 'ID' is successful",
                    tvaultconf.PASS)

            out = cli_parser.cli_output(cmd)
            LOG.debug("Response from CLI: " + str(out))
            if (policy_id in out):
                reporting.add_test_step(
                    "Verify list_assigned_policy shows policy_id only", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify list_assigned_policy shows policy_id only", tvaultconf.FAIL)

            # Verify policy assigned to tenant by admin user using list_assigned_policies cli
            cmd = command_argument_string.list_assigned_policies + admin_project_id + " -c Name -f value"
            LOG.debug("cli command: {}".format(cmd))
            rc = cli_parser.cli_returncode(cmd)
            if rc != 0:
                reporting.add_test_step(
                    "Execute list_assigned_policies command with column 'Name' is successful",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Execute list_assigned_policies command with column 'Name' is successful",
                    tvaultconf.PASS)

            out = cli_parser.cli_output(cmd)
            LOG.debug("Response from CLI: " + str(out))
            if (tvaultconf.policy_name_update in out):
                reporting.add_test_step(
                    "Verify list_assigned_policy shows policy_name only", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify list_assigned_policy shows policy_name only", tvaultconf.FAIL)

            # Verify policy assigned to tenant by admin user using list_assigned_policies cli
            cmd = command_argument_string.list_assigned_policies + admin_project_id + " -f table"
            LOG.debug("cli command: {}".format(cmd))
            rc = cli_parser.cli_returncode(cmd)
            if rc != 0:
                reporting.add_test_step(
                    "Execute list_assigned_policies command with '-f table' is successful",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Execute list_assigned_policies command with '-f table' is successful",
                    tvaultconf.PASS)

            out = cli_parser.cli_output(cmd)
            LOG.debug("Response from CLI: " + str(out))
            cli_output_table = out.strip()
            table_format = '| ' + policy_id + ' |'

            if table_format in cli_output_table:
                reporting.add_test_step(
                    "Verify list_assigned_policy shows output in table format", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify list_assigned_policy shows output in table format", tvaultconf.FAIL)

            # Verify policy assigned to tenant by admin user using list_assigned_policies cli
            cmd = command_argument_string.list_assigned_policies + admin_project_id + " -f json"
            LOG.debug("cli command: {}".format(cmd))
            rc = cli_parser.cli_returncode(cmd)
            if rc != 0:
                reporting.add_test_step(
                    "Execute list_assigned_policies command with '-f json' is successful",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Execute list_assigned_policies command with '-f json' is successful",
                    tvaultconf.PASS)

            out = cli_parser.cli_output(cmd)
            LOG.debug("Response from CLI: " + str(out))
            cli_output_json = out.replace("\n", "").strip()
            json_format = '[  {    "ID": "' + policy_id + '",'

            if json_format in cli_output_json:
                reporting.add_test_step(
                    "Verify list_assigned_policy shows output in json format", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify list_assigned_policy shows output in json format", tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @test.pre_req({'type': 'small_workload'})
    @decorators.attr(type='workloadmgr_cli')
    def test_5_workload_modify(self):
        reporting.add_test_script(str(__name__) + "_workload_modify")
        try:
            if self.exception != "":
                LOG.debug("pre req failed")
                reporting.add_test_step(str(self.exception), tvaultconf.FAIL)
                raise Exception(str(self.exception))
            LOG.debug("pre req completed")
            global vm_id
            global policy_id
            global volume_id
            volume_id = self.volume_id
            vm_id = self.vm_id

            # Use admin credentials
            os.environ['OS_USERNAME'] = CONF.identity.username
            os.environ['OS_PASSWORD'] = CONF.identity.password

            # Assign workload policy to projects
            project_id = CONF.identity.tenant_id
            status = self.assign_unassign_workload_policy(
                str(policy_id), add_project_ids_list=[project_id], remove_project_ids_list=[])

            # Create workload with policy by CLI command
            workload_create = command_argument_string.workload_create + \
                " instance-id=" + \
                str(vm_id) + " --policy-id " + str(policy_id)
            rc = cli_parser.cli_returncode(workload_create)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-create with policy command",
                    tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-create with policy command",
                    tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            time.sleep(10)
            workload_id = query_data.get_workload_id_in_creation(tvaultconf.workload_name)
            LOG.debug("Created workload ID: " + str(workload_id))
            if(workload_id != ""):
                self.wait_for_workload_tobe_available(workload_id)
                if(self.getWorkloadStatus(workload_id) == "available"):
                    reporting.add_test_step(
                        "Create workload with policy", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Create workload with policy", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Create workload with policy", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # Verify that workload is created with same policy ID
            workload_details = self.get_workload_details(workload_id)
            policyid_from_workload_metadata = workload_details["metadata"]["policy_id"]
            if policyid_from_workload_metadata == policy_id:
                reporting.add_test_step(
                    "Verfiy that same policy id is assigned in workload-metadata",
                    tvaultconf.PASS)
                LOG.debug("Same policy id is assigned in workload-metadata")
            else:
                reporting.add_test_step(
                    "Verfiy that same policy id is assigned in workload-metadata",
                    tvaultconf.FAIL)
                raise Exception(
                    "policy id not assigned properly in workload-metadata")

            # Verify that workload is created with same policy settings
            key_list = ["fullbackup_interval", "retention_policy_type",
                        "interval", "retention_policy_value"]
            same_policy_settings = True
            policy_details = self.get_policy_details(policy_id)
            if not policy_details:
                reporting.add_test_step("Get policy details", tvaultconf.FAIL)
                raise Exception("Get policy details failed")
            else:
                field_values = policy_details[1]
            for i in key_list:
                if workload_details["jobschedule"][i] != field_values[i]:
                    same_policy_settings = False
                    break
            if same_policy_settings:
                reporting.add_test_step(
                    "Verify that workload is created with same policy settings",
                    tvaultconf.PASS)
                LOG.debug("Workload is created with same policy settings")
            else:
                reporting.add_test_step(
                    "Verify that workload is created with same policy settings",
                    tvaultconf.FAIL)
                LOG.debug("Workload is not created with same policy settings")

            # Launch second instance
            self.vm_id2 = self.create_vm()
            LOG.debug("VM ID2: " + str(self.vm_id2))

            # Create volume
            self.volume_id2 = self.create_volume()
            LOG.debug("Volume ID2: " + str(self.volume_id2))

            # Attach volume to the instance
            self.attach_volume(self.volume_id2, self.vm_id2)
            LOG.debug("Volume2 attached")

            # Modify workload to add new instance using CLI command
            workload_modify_command = command_argument_string.workload_modify + " --instance instance-id=" + \
                str(self.vm_id2) + " --instance instance-id=" + str(vm_id) + " " + str(workload_id)
            rc = cli_parser.cli_returncode(workload_modify_command)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-modify command to add one more vm",
                    tvaultconf.FAIL)
                LOG.error("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-modify command to add one more vm",
                    tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            self.wait_for_workload_tobe_available(workload_id)
            workload_vm_count = query_data.get_available_vms_of_workload(
                workload_id)
            if (workload_vm_count == 2):
                reporting.add_test_step(
                    "Verify vm added to policy assigned workload with DB",
                    tvaultconf.PASS)
                LOG.debug("Vm has been added successfully")
            else:
                reporting.add_test_step(
                    "Verify vm added to policy assigned workload with DB",
                    tvaultconf.FAIL)
                LOG.error("Vm has not been added")

            # workload delete
            self.workload_delete(workload_id)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_6_workload_policy_in_use(self):
        reporting.add_test_script(str(__name__) + "_in_use")
        try:
            global vm_id
            global policy_id
            # Create workload with policy by CLI command
            workload_create = command_argument_string.workload_create + \
                " instance-id=" + \
                str(vm_id) + " --policy-id " + str(policy_id)
            rc = cli_parser.cli_returncode(workload_create)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-create with policy command",
                    tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-create with policy command",
                    tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            time.sleep(10)
            workload_id = query_data.get_workload_id_in_creation(tvaultconf.workload_name)
            LOG.debug("Created workload ID: " + str(workload_id))
            if(workload_id != ""):
                self.wait_for_workload_tobe_available(workload_id)
                if(self.getWorkloadStatus(workload_id) == "available"):
                    reporting.add_test_step(
                        "Create workload with policy", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Create workload with policy", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Create workload with policy", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # Verify policy can not be updated when it is in use
            updated_status = self.workload_policy_update(
                policy_id,
                policy_name=tvaultconf.policy_name_update,
                fullbackup_interval=tvaultconf.fullbackup_interval_update,
                interval=tvaultconf.interval_update,
                retention_policy_value=tvaultconf.retention_policy_value_update)
            if updated_status:
                reporting.add_test_step(
                    "Can not update policy while in use", tvaultconf.FAIL)
                raise Exception(
                    "Workload policy has been updated while in use")
            else:
                reporting.add_test_step(
                    "Can not update policy while in use", tvaultconf.PASS)
                LOG.debug("Workload policy has not been updated while in use")

            # Verify policy assigned to tenant by admin user using list_assigned_policies cli
            cmd = command_argument_string.list_assigned_policies + CONF.identity.tenant_id
            rc = cli_parser.cli_returncode(cmd)
            if rc != 0:
                reporting.add_test_step(
                    "Execute list_assigned_policies command is successful",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Execute list_assigned_policies command is successful",
                    tvaultconf.PASS)

            out = cli_parser.cli_output(cmd)
            LOG.debug("Response from CLI: " + str(out))
            if (policy_id in out):
                reporting.add_test_step(
                    "Verify list_assigned_policy shows assigned project_id", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify list_assigned_policy shows assigned project_id", tvaultconf.FAIL)

            # Verify policy can not be deleted when it is in use
            delete_status = self.workload_policy_delete(policy_id)
            if delete_status:
                reporting.add_test_step(
                    "Can not delete policy when in use", tvaultconf.FAIL)
                raise Exception("Policy deleted which is in use")
            else:
                reporting.add_test_step(
                    "Can not delete policy when in use", tvaultconf.PASS)
                LOG.debug("Policy not deleted which is in use")

            # Delete workload before deleting policy
            status = self.workload_delete(workload_id)
            if status:
                LOG.debug("workload deleted successfully")
            else:
                raise Exception("workload deleted unsuccessfully")
            time.sleep(10)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_7_workload_policy_delete(self):
        reporting.add_test_script(str(__name__) + "_delete")
        try:
            global policy_id
            policy_delete_error_str = "Policy doesn't allow workload:policy_delete to be performed."
            failed = False

            # Use non-admin credentials
            os.environ['OS_USERNAME'] = CONF.identity.nonadmin_user
            os.environ['OS_PASSWORD'] = CONF.identity.nonadmin_password

            # Delete workload policy by nonadmin user using CLI
            policy_delete_command = command_argument_string.policy_delete + \
                str(policy_id)
            error = cli_parser.cli_error(policy_delete_command)
            if error and (str(error.strip('\n')).find(policy_delete_error_str) != -1):
                reporting.add_test_step(
                    "Can not delete workload policy by nonadmin user",
                    tvaultconf.PASS)
                LOG.debug("Policy is not deleted by nonadmin user")
            else:
                reporting.add_test_step(
                    "Can not delete workload policy by nonadmin user",
                    tvaultconf.FAIL)
                failed = True

            # Use admin credentials
            os.environ['OS_USERNAME'] = CONF.identity.username
            os.environ['OS_PASSWORD'] = CONF.identity.password

            # Policy delete when it is not in use
            delete_status = self.workload_policy_delete(policy_id)
            if delete_status:
                reporting.add_test_step(
                    "Delete policy which is assigned to tenant by admin user",
                    tvaultconf.PASS)
                LOG.debug("Policy deleted")
            else:
                reporting.add_test_step(
                    "Delete policy which is assigned to tenant by admin user",
                    tvaultconf.FAIL)
                failed = True

            # Verify policy is deleted
            policy_list = self.get_policy_list()
            if not policy_list:
                LOG.debug("Policy list not available")
                reporting.add_test_step(
                    "Verify policy deleted", tvaultconf.PASS)
            else:
                if policy_id in policy_list:
                    reporting.add_test_step(
                        "Verify policy deleted", tvaultconf.FAIL)
                    failed = True
                else:
                    reporting.add_test_step(
                        "Verify policy deleted", tvaultconf.PASS)
                    LOG.debug("Policy deleted passed")

            # Verify policy assigned to tenant by admin user using list_assigned_policies cli
            cmd = command_argument_string.list_assigned_policies + CONF.identity.tenant_id
            rc = cli_parser.cli_returncode(cmd)
            if rc != 0:
                reporting.add_test_step(
                    "Execute list_assigned_policies command is successful",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Execute list_assigned_policies command is successful",
                    tvaultconf.PASS)

            out = cli_parser.cli_output(cmd)
            LOG.debug("Response from CLI: " + str(out))
            if (CONF.identity.tenant_id not in out):
                reporting.add_test_step(
                    "Verify list_assigned_policy shows assigned project_id", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify list_assigned_policy shows assigned project_id", tvaultconf.FAIL)

            # DB validations for workload policy after workload cleanup
            workload_policy_fields_data = query_data.get_workload_policy_fields()
            LOG.debug("Get workload policy fields data: {}".format(workload_policy_fields_data))

            if (tvaultconf.workload_policy_fields == workload_policy_fields_data):
                LOG.debug("workload policy fields data is correct")
            else:
                reporting.add_test_step("workload policy fields data is in-correct", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            workload_policy_validations_after_deletion = self.db_cleanup_workload_policy_validations(policy_id)
            if (all(value == 0 for value in workload_policy_validations_after_deletion.values())):
                reporting.add_test_step("db cleanup validations for workload policy", tvaultconf.PASS)
            else:
                reporting.add_test_step("db cleanup validations for workload policy", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            if failed:
                reporting.set_test_script_status(tvaultconf.FAIL)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    # Workload policy with scheduler and retension parameter
    @decorators.attr(type='workloadmgr_cli')
    def test_8_policywith_scheduler_retension(self):
        reporting.add_test_script(str(__name__) + "_with_scheduler_retention")
        try:
            global vm_id
            global volume_id
            snapshots_list = []
            # Create workload with scheduler enabled using CLI
            workload_create = command_argument_string.workload_create + \
                " instance-id=" + \
                str(vm_id) + " --jobschedule enabled=True"
            LOG.debug("WORKLOAD CMD - " + str(workload_create))
            error = cli_parser.cli_error(workload_create)
            if error and (str(error.strip('\n')).find('ERROR') != -1):
                LOG.debug("workload creation unsuccessful : " + error)
                reporting.add_test_step(
                    "Execute workload-create command with scheduler enable",
                    tvaultconf.FAIL)
                raise Exception(
                    "Command workload create did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-create command with scheduler enable",
                    tvaultconf.PASS)
                LOG.debug("Command workload create executed correctly")

            time.sleep(20)
            self.workload_id = query_data.get_workload_id_in_creation(
                tvaultconf.workload_name)
            LOG.debug("Created workload ID: " + str(self.workload_id))
            if self.workload_id is not None:
                self.wait_for_workload_tobe_available(self.workload_id)
                if(self.getWorkloadStatus(self.workload_id) == "available"):
                    reporting.add_test_step(
                        "Create workload with scheduler enable", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Create workload with scheduler enable", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Create workload with scheduler enable", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # Verify workload created with scheduler enable
            status = self.getSchedulerStatus(self.workload_id)
            if status:
                reporting.add_test_step(
                    "Verify workload created with scheduler enabled",
                    tvaultconf.PASS)
                LOG.debug("Workload created with scheduler enabled successfully")
            else:
                reporting.add_test_step(
                    "Verify workload created with scheduler enabled",
                    tvaultconf.FAIL)
                raise Exception(
                    "Workload has not been created with scheduler enabled")

            # Get retension parameters values of wid wirh scheduler enabled
            retention_policy_type_wid = self.getRetentionPolicyTypeStatus(
                self.workload_id)
            retention_policy_value_wid = self.getRetentionPolicyValueStatus(
                self.workload_id)
            Full_Backup_Interval_Value_wid = self.getFullBackupIntervalStatus(
                self.workload_id)

            # Launch second instance
            self.vm_id2 = self.create_vm()
            LOG.debug("VM ID2: " + str(self.vm_id2))

            # Create volume
            self.volume_id2 = self.create_volume()
            LOG.debug("Volume ID2: " + str(self.volume_id2))

            # Attach volume to the instance
            self.attach_volume(self.volume_id2, self.vm_id2)
            LOG.debug("Volume2 attached")

            # Create workload with scheduler disabled using CLI
            workload_create = command_argument_string.workload_create + \
                " instance-id=" + \
                str(self.vm_id2) + " --jobschedule enabled=False"
            rc = cli_parser.cli_returncode(workload_create)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-create command with scheduler disable",
                    tvaultconf.FAIL)
                raise Exception(
                    "Command workload create did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-create command with scheduler disable",
                    tvaultconf.PASS)
                LOG.debug("Command workload create executed correctly")

            time.sleep(10)
            self.workload_id2 = query_data.get_workload_id_in_creation(
                tvaultconf.workload_name)
            LOG.debug("Workload2 ID: " + str(self.workload_id2))
            if(self.workload_id2 is not None):
                self.wait_for_workload_tobe_available(self.workload_id2)
                if(self.getWorkloadStatus(self.workload_id2) == "available"):
                    reporting.add_test_step(
                        "Create workload with scheduler disable", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Create workload with scheduler disable", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Create workload with scheduler disable", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # Verify workload created scheduler disable
            status = self.getSchedulerStatus(self.workload_id2)
            if status:
                reporting.add_test_step(
                    "Verify workload created with scheduler disable",
                    tvaultconf.FAIL)
                raise Exception(
                    "Workload has not been created with scheduler disabled")
            else:
                reporting.add_test_step(
                    "Verify workload created with scheduler disable",
                    tvaultconf.PASS)
                LOG.debug(
                    "Workload created with scheduler disabled successfully")

            # Get retension parameters values of workload_id2 wirh scheduler
            # disabled
            retention_policy_type_wid2 = self.getRetentionPolicyTypeStatus(
                self.workload_id2)
            retention_policy_value_wid2 = self.getRetentionPolicyValueStatus(
                self.workload_id2)
            Full_Backup_Interval_Value_wid2 = self.getFullBackupIntervalStatus(
                self.workload_id2)

            # Create workload policy
            self.policy_id = self.workload_policy_create(
                fullbackup_interval=tvaultconf.fullbackup_interval,
                retention_policy_value=tvaultconf.retention_policy_value,
                retention_policy_type=tvaultconf.retention_policy_type,
                policy_cleanup=True)
            if self.policy_id != "":
                reporting.add_test_step(
                    "Create workload policy", tvaultconf.PASS)
                LOG.debug("Workload policy id is " + str(self.policy_id))
            else:
                reporting.add_test_step(
                    "Create workload policy", tvaultconf.FAIL)
                raise Exception("Workload policy has not been created")

            # Assign workload policy to projects
            project_id = CONF.identity.tenant_id
            status = self.assign_unassign_workload_policy(
                self.policy_id, add_project_ids_list=[project_id], remove_project_ids_list=[])
            if status:
                reporting.add_test_step(
                    "Assign workload policy", tvaultconf.PASS)
                LOG.debug("Workload policy is assigned to project")
            else:
                reporting.add_test_step(
                    "Assign workload policy", tvaultconf.FAIL)
                raise Exception("Workload policy is not assigned")

            # Verify after policy assigned to tenant does not alter earlier workload retension parameters
            # Get retension parameters values of wid wirh scheduler enabled
            retention_policy_type_w1 = self.getRetentionPolicyTypeStatus(
                self.workload_id)
            retention_policy_value_w1 = self.getRetentionPolicyValueStatus(
                self.workload_id)
            Full_Backup_Interval_Value_w1 = self.getFullBackupIntervalStatus(
                self.workload_id)

            # Get retension parameters values of wid_2 wirh scheduler disabled
            retention_policy_type_w2 = self.getRetentionPolicyTypeStatus(
                self.workload_id2)
            retention_policy_value_w2 = self.getRetentionPolicyValueStatus(
                self.workload_id2)
            Full_Backup_Interval_Value_w2 = self.getFullBackupIntervalStatus(
                self.workload_id2)

            if retention_policy_type_w1 == retention_policy_type_wid and retention_policy_value_w1 == retention_policy_value_wid and Full_Backup_Interval_Value_w1\
                == Full_Backup_Interval_Value_wid:
                reporting.add_test_step(
                    "Scheduler enabled workload Retension param's preserve after policy assign to tenant",
                    tvaultconf.PASS)
                LOG.debug(
                    "workload with scheduler enabled Retension param's preserved")
            else:
                reporting.add_test_step(
                    "Scheduler enabled workload Retension param's preserve after policy assign to tenant",
                    tvaultconf.FAIL)
                raise Exception(
                    "workload with scheduler enabled Retension param's not preserved")

            if retention_policy_type_w2 == retention_policy_type_wid2 and retention_policy_value_w2 == retention_policy_value_wid2 and Full_Backup_Interval_Value_w2\
                == Full_Backup_Interval_Value_wid2:
                reporting.add_test_step(
                    "Scheduler disabled workload Retension param's preserve after policy assign to tenant",
                    tvaultconf.PASS)
                LOG.debug(
                    "workload with scheduler disabled Retension param's preserved")
            else:
                reporting.add_test_step(
                    "Scheduler disabled workload Retension param's preserve after policy assign to tenant",
                    tvaultconf.FAIL)
                raise Exception(
                    "workload with scheduler disabled Retension param's not preserved")

            # Modify policy of scheduler enabled workload
            workload_modify_command = command_argument_string.workload_modify + \
                "--policy-id " + str(self.policy_id) + \
                " " + str(self.workload_id)
            rc = cli_parser.cli_returncode(workload_modify_command)
            if rc != 0:
                reporting.add_test_step(
                    "Execute scheduler enabled workload policy modify command",
                    tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute scheduler enabled workload policy modify command",
                    tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            # Modify policy of scheduler disabled workload
            workload_modify_command = command_argument_string.workload_modify + \
                "--policy-id " + str(self.policy_id) + \
                " " + str(self.workload_id2)
            rc = cli_parser.cli_returncode(workload_modify_command)
            if rc != 0:
                reporting.add_test_step(
                    "Execute scheduler disabled workload policy modify command",
                    tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute scheduler disabled workload policy modify command",
                    tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            # Verify policy is reflected after workload policy modify
            # Get retension parameters values of workload_id wirh scheduler
            # disabled
            retention_policy_type_w1 = self.getRetentionPolicyTypeStatus(
                self.workload_id)
            retention_policy_value_w1 = self.getRetentionPolicyValueStatus(
                self.workload_id)
            Full_Backup_Interval_Value_w1 = self.getFullBackupIntervalStatus(
                self.workload_id)
            # Get retension parameters values of workload_id2 wirh scheduler
            # disabled
            retention_policy_type_w2 = self.getRetentionPolicyTypeStatus(
                self.workload_id2)
            retention_policy_value_w2 = self.getRetentionPolicyValueStatus(
                self.workload_id2)
            Full_Backup_Interval_Value_w2 = self.getFullBackupIntervalStatus(
                self.workload_id2)

            if retention_policy_type_w1 == tvaultconf.retention_policy_type and retention_policy_value_w1 == tvaultconf.retention_policy_value and \
                Full_Backup_Interval_Value_w1 == tvaultconf.fullbackup_interval:
                reporting.add_test_step(
                    "Scheduler enabled workload Retension param's updated after policy modify",
                    tvaultconf.PASS)
                LOG.debug("Scheduler enabled workload policy param's modified")
            else:
                reporting.add_test_step(
                    "Scheduler enabled workload Retension param's updated after policy modify",
                    tvaultconf.FAIL)
                raise Exception(
                    "Scheduler enabled workload policy param's not modified")

            if retention_policy_type_w2 == tvaultconf.retention_policy_type and retention_policy_value_w2 == tvaultconf.retention_policy_value and \
                Full_Backup_Interval_Value_w2 == tvaultconf.fullbackup_interval:
                reporting.add_test_step(
                    "Scheduler disabled workload Retension param's updated after policy modify",
                    tvaultconf.PASS)
                LOG.debug("Scheduler disabled workload policy param's modified")
            else:
                reporting.add_test_step(
                    "Scheduler disabled workload Retension param's updated after policy modify",
                    tvaultconf.FAIL)
                raise Exception(
                    "Scheduler disabled workload policy param's not modified")

            # Create workload policy_2
            self.policy_id2 = self.workload_policy_create(
                fullbackup_interval=tvaultconf.fullbackup_interval,
                retention_policy_value=tvaultconf.retention_policy_value,
                retention_policy_type=tvaultconf.retention_policy_type,
                policy_cleanup=False)
            if self.policy_id2 != "":
                reporting.add_test_step(
                    "Create workload policy to replace old one",
                    tvaultconf.PASS)
                LOG.debug("Workload policy id is " + str(self.policy_id2))
            else:
                reporting.add_test_step(
                    "Create workload policy to replace old one",
                    tvaultconf.FAIL)
                raise Exception("Workload policy has not been created")

            # Assign workload policy to projects
            project_id = CONF.identity.tenant_id
            status = self.assign_unassign_workload_policy(
                self.policy_id2, add_project_ids_list=[project_id], remove_project_ids_list=[])
            if status:
                reporting.add_test_step(
                    "Assign workload policy_2", tvaultconf.PASS)
                LOG.debug("Workload policy_2 is assigned to project")
            else:
                reporting.add_test_step(
                    "Assign workload policy_2", tvaultconf.FAIL)
                raise Exception("Workload policy_2 is not assigned to project")

            # Modify policy1 to policy2 of scheduler enabled workload
            workload_modify_command = command_argument_string.workload_modify + \
                "--policy-id " + str(self.policy_id2) + \
                " " + str(self.workload_id)
            rc = cli_parser.cli_returncode(workload_modify_command)
            if rc != 0:
                reporting.add_test_step(
                    "Scheduler enabled workload modify policy1 to policy2",
                    tvaultconf.FAIL)
                raise Exception(
                    "Command did not execute modify policy1 to policy2 correctly")
            else:
                reporting.add_test_step(
                    "Scheduler enabled workload modify policy1 to policy2",
                    tvaultconf.PASS)
                LOG.debug("Command modify policy1 to policy2 execute correctly")

            # Modify policy1 to policy2  of scheduler disabled workload
            workload_modify_command = command_argument_string.workload_modify + \
                "--policy-id " + str(self.policy_id2) + \
                " " + str(self.workload_id2)
            rc = cli_parser.cli_returncode(workload_modify_command)
            if rc != 0:
                reporting.add_test_step(
                    "Scheduler disabled workload modify policy1 to policy2",
                    tvaultconf.FAIL)
                raise Exception(
                    "Command modify did not execute policy1 to policy2 correctly")
            else:
                reporting.add_test_step(
                    "Scheduler disabled workload modify policy1 to policy2",
                    tvaultconf.PASS)
                LOG.debug("Command modify policy1 to policy2 execute correctly")

            # Verify after modify policy_1 to policy_2
            # Get retension parameters values of wid_2 wirh scheduler disabled
            retention_policy_type_w1 = self.getRetentionPolicyTypeStatus(
                self.workload_id)
            retention_policy_value_w1 = self.getRetentionPolicyValueStatus(
                self.workload_id)
            Full_Backup_Interval_Value_w1 = self.getFullBackupIntervalStatus(
                self.workload_id)

            # Get retension parameters values of wid_2 wirh scheduler disabled
            retention_policy_type_w2 = self.getRetentionPolicyTypeStatus(
                self.workload_id2)
            retention_policy_value_w2 = self.getRetentionPolicyValueStatus(
                self.workload_id2)
            Full_Backup_Interval_Value_w2 = self.getFullBackupIntervalStatus(
                self.workload_id2)

            if retention_policy_type_w1 == tvaultconf.retention_policy_type and retention_policy_value_w1 == tvaultconf.retention_policy_value and \
                Full_Backup_Interval_Value_w1 == tvaultconf.fullbackup_interval:
                reporting.add_test_step(
                    "Verify Scheduler enabled workload modified policy_1 to policy_2",
                    tvaultconf.PASS)
                LOG.debug(
                    "Scheduler enabled workload modified policy_1 to policy_2")
            else:
                reporting.add_test_step(
                    "Verify Scheduler enabled workload modified policy_1 to policy_2",
                    tvaultconf.FAIL)
                raise Exception(
                    "Scheduler enabled workload not modified policy_1 to policy_2")

            if retention_policy_type_w2 == tvaultconf.retention_policy_type and retention_policy_value_w2 == tvaultconf.retention_policy_value and \
                Full_Backup_Interval_Value_w2 == tvaultconf.fullbackup_interval:
                reporting.add_test_step(
                    "Verify Scheduler disabled workload modified policy_1 to policy_2",
                    tvaultconf.PASS)
                LOG.debug(
                    "Scheduler disabled workload modified policy_1 to policy_2")
            else:
                reporting.add_test_step(
                    "Scheduler disabled workload modified policy_1 to policy_2",
                    tvaultconf.FAIL)
                raise Exception(
                    "Scheduler disabled workload not modified policy_1 to policy_2")

            # Retension meets as mentioned value in the workload policy
            # Create snapshots equal to number of retention_policy_value
            for i in range(0, int(retention_policy_value_w1)):
                snapshot_id = self.workload_snapshot(
                    self.workload_id,
                    True,
                    snapshot_name=tvaultconf.snapshot_name +
                    str(i),
                    snapshot_cleanup=False)
                snapshots_list.append(snapshot_id)
            LOG.debug("snapshot id list is : " + str(snapshots_list))

            # Create one more snapshot
            snapshot_id = self.workload_snapshot(
                self.workload_id,
                True,
                snapshot_name=tvaultconf.snapshot_name +
                "_final",
                snapshot_cleanup=False)
            LOG.debug("Last snapshot id is : " + str(snapshot_id))

            self.wait_for_snapshot_tobe_available(
                self.workload_id, snapshot_id)
            LOG.debug("wait for snapshot available state")

            snapshots_list.append(snapshot_id)
            LOG.debug("final snapshot list is " + str(snapshots_list))

            # get snapshot count and snapshot_details
            snapshot_list_of_workload = self.getSnapshotListWithNoError(self.workload_id)
            LOG.debug("Available snapshot list of workload retrieved using API is : " +
                      str(snapshot_list_of_workload))

            # verify that numbers of snapshot created persist
            # retention_policy_value
            LOG.debug("number of snapshots created : %d " %
                      len(snapshot_list_of_workload))
            if int(retention_policy_value_w1) == len(
                snapshot_list_of_workload):
                reporting.add_test_step(
                    "Verify number of snapshots created equals retention_policy_value",
                    tvaultconf.PASS)
                LOG.debug(
                    "Number of snapshots created equals retention_policy_value")
            else:
                reporting.add_test_step(
                    "Verify number of snapshots created equals retention_policy_value",
                    tvaultconf.FAIL)
                raise Exception(
                    "Number of snapshots created not equal to retention_policy_value")

            # Check first snapshot is deleted or not after retension value
            # exceed
            deleted_snapshot_id = snapshots_list[0]
            LOG.debug("snapshot id of first snapshot is : " +
                      str(deleted_snapshot_id))
            if deleted_snapshot_id in snapshot_list_of_workload:
                reporting.add_test_step(
                    "Verify first snapshot deleted after retension value exceeds",
                    tvaultconf.FAIL)
                raise Exception(
                    "first snapshot not deleted after retension value exceeds")
            else:
                reporting.add_test_step(
                    "Verify first snapshot deleted after retension value exceeds",
                    tvaultconf.PASS)
                LOG.debug("first snapshot deleted after retension value exceeds")

            # Check first snapshot is deleted from backup target when retension
            # value exceed
            mount_path = self.get_mountpoint_path()
            LOG.debug("Backup target mount_path is : " + mount_path)
            is_snapshot_exist = self.check_snapshot_exist_on_backend(
                mount_path, self.workload_id, deleted_snapshot_id)
            LOG.debug("Snapshot does not exist : %s" % is_snapshot_exist)
            if not is_snapshot_exist:
                LOG.debug("First snapshot is deleted from backup target")
                reporting.add_test_step(
                    "First snapshot deleted from backup target",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "First snapshot deleted from backup target",
                    tvaultconf.FAIL)
                raise Exception(
                    "First snapshot is not deleted from backup target media")

            # Get policies list assigned to tenant
            # Multiple policies to single tenant
            assigned_policies = self.assigned_policies(CONF.identity.tenant_id)
            if assigned_policies and len(assigned_policies) > 1:
                reporting.add_test_step(
                    "List policies assigned to specific tenant",
                    tvaultconf.PASS)
                LOG.debug("Policies assigned to project %s are %s" %
                          (CONF.identity.tenant_id, assigned_policies))
                reporting.add_test_step(
                    "Multiple policies assigned one by one to tenant",
                    tvaultconf.PASS)
                LOG.debug("Multiple policies assigned to project %s are %s" % (
                    CONF.identity.tenant_id, assigned_policies))
            else:
                reporting.add_test_step(
                    "List policies assigned one by one to tenant",
                    tvaultconf.FAIL)
                reporting.add_test_step(
                    "Multiple policies assigned to specific tenant",
                    tvaultconf.FAIL)
                raise Exception(
                    "Listing policies assigned to specific tenant failed")

            # Single policy to multiple tenant
            project_id = CONF.identity.tenant_id_1
            admin_project_id = CONF.identity.tenant_id
            status = self.assign_unassign_workload_policy(
                self.policy_id, add_project_ids_list=[project_id], remove_project_ids_list=[])
            # below function returns list as [policy_name, field_values,
            # policy_id, description, list_of_project_assigned]
            details = self.get_policy_details(self.policy_id)
            if not details:
                reporting.add_test_step("Get policy details", tvaultconf.FAIL)
                raise Exception("Get policy details failed")
            else:
                if project_id in details[4] and admin_project_id in details[4] and len(
                    details[4]) == 2:
                    reporting.add_test_step(
                        "Single policy to multiple tenant", tvaultconf.PASS)
                    LOG.debug(
                        "Single policy assigned to multiple tenant successfully")
                else:
                    reporting.add_test_step(
                        "Single policy to multiple tenant", tvaultconf.FAIL)
                    raise Exception(
                        "Single policy assigned to multiple tenant unsuccessfully")

            # Modify workload scheduler to disable using CLI command
            workload_modify_command = command_argument_string.workload_modify + \
                "--jobschedule enabled=False " + str(self.workload_id)
            rc = cli_parser.cli_returncode(workload_modify_command)
            if rc != 0:
                reporting.add_test_step(
                    "Execute policy assigned workload-modify scheduler disable",
                    tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute policy assigned workload-modify scheduler disable",
                    tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            # Verify workload with policy scheduler changed to disable
            status = self.getSchedulerStatus(self.workload_id)
            if status:
                reporting.add_test_step(
                    "Verify policy assigned workload scheduler disabled",
                    tvaultconf.FAIL)
                raise Exception(
                    "Policy assigned workload scheduler disabled unsuccessfully")
            else:
                reporting.add_test_step(
                    "Verify policy assigned workload scheduler disabled",
                    tvaultconf.PASS)
                LOG.debug(
                    "Policy assigned workload scheduler disabled successfully")

            # Modify workload with policy scheduler to enable
            workload_modify_command = command_argument_string.workload_modify + \
                "--jobschedule enabled=True " + str(self.workload_id2)
            rc = cli_parser.cli_returncode(workload_modify_command)
            if rc != 0:
                reporting.add_test_step(
                    "Execute policy assigned workload-modify scheduler enable",
                    tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute policy assigned workload-modify scheduler enable",
                    tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            # Verify workload with policy scheduler changed to enable
            self.wait_for_workload_tobe_available(self.workload_id2)
            status = self.getSchedulerStatus(self.workload_id2)
            if status:
                reporting.add_test_step(
                    "Verify policy assigned workload scheduler enabled",
                    tvaultconf.PASS)
                LOG.debug(
                    "Policy assigned workload scheduler enabled successfully")
            else:
                reporting.add_test_step(
                    "Verify policy assigned workload scheduler enabled",
                    tvaultconf.FAIL)
                raise Exception(
                    "Policy assigned workload scheduler enabled unsuccessfully")

            # Cleanup
            # Delete snapshot
            snapshot_list_of_workload = self.getSnapshotList(self.workload_id)
            for i in range(0, len(snapshot_list_of_workload)):
                self.snapshot_delete(
                    self.workload_id, snapshot_list_of_workload[i])

            # Delete workload
            self.workload_delete(self.workload_id)
            self.workload_delete(self.workload_id2)

            # Delete policy
            self.workload_policy_delete(self.policy_id)
            self.workload_policy_delete(self.policy_id2)

            # DB validations for workload policy after workload cleanup
            workload_policy_fields_data = query_data.get_workload_policy_fields()
            if (tvaultconf.workload_policy_fields == workload_policy_fields_data):
                LOG.debug("workload policy fields data is correct")
            else:
                reporting.add_test_step("workload policy fields data is in-correct", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            workload_policy_validations_after_deletion = self.db_cleanup_workload_policy_validations(self.policy_id)
            if (all(value == 0 for value in workload_policy_validations_after_deletion.values())):
                reporting.add_test_step("db cleanup validations for workload policy-1", tvaultconf.PASS)
            else:
                reporting.add_test_step("db cleanup validations for workload policy-1", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            workload_policy_validations_after_deletion = self.db_cleanup_workload_policy_validations(self.policy_id2)
            if (all(value == 0 for value in workload_policy_validations_after_deletion.values())):
                reporting.add_test_step("db cleanup validations for workload policy-2", tvaultconf.PASS)
            else:
                reporting.add_test_step("db cleanup validations for workload policy-2", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()
            # Delete vm
            self.delete_vm(vm_id)
            LOG.debug("vm deleted succesfully")

            # delete volume
            self.delete_volume(volume_id)
            LOG.debug("volume deleted successfully")

