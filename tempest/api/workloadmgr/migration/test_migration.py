import os
import sys
import json

from oslo_log import log as logging

from tempest import config
from tempest import reporting
from tempest import tvaultconf
from tempest.api.workloadmgr import base
from tempest.lib import decorators
from tempest.util import query_data
from tempest import command_argument_string
from tempest.util import cli_parser

sys.path.append(os.getcwd())

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    @decorators.attr(type='workloadmgr_api')
    def test_01_migration(self):
        try:
            reporting.add_test_script(str(__name__) + \
                    "_create_migration_plan_api")
            self.vms = self.get_migration_test_vms(vm_list= \
                            self.get_vcenter_vms())
            self.plan_id, self.err_str = self.create_migration_plan(self.vms)
            LOG.debug(f"Plan ID returned from API: {self.plan_id}")
            LOG.error(f"Error: {self.err_str}")
            if self.plan_id:
                reporting.add_test_step("Create Migration Plan", tvaultconf.PASS)
            else:
                raise Exception("Create Migration Plan")

            #DB verification
            self.wait_for_migrationplan_tobe_available(self.plan_id)
            self.plan_db = query_data.get_migration_plan(self.plan_id)
            LOG.debug(f"Plan details from DB: {self.plan_db}")
            if self.plan_db[0] == tvaultconf.migration_plan_name and \
                self.plan_db[1] == "available":
                reporting.add_test_step("DB verification", tvaultconf.PASS)
            else:
                raise Exception("DB verification")

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_02_migration(self):
        try:
            reporting.add_test_script(str(__name__) + \
                    "_create_migration_plan_cli")
            vm_str = ""
            self.plan_id = None
            cli_error_str = "is already part of another migration plan"
            self.vms = self.get_migration_test_vms(vm_list= \
                            self.get_vcenter_vms())
            for vm in self.vms:
                vm_str += " " + vm

            mp_create = command_argument_string.migration_plan_create +\
                    vm_str
            out = cli_parser.cli_output(mp_create)
            if out:
                self.plan_id = json.loads(out)[0]['ID']
                LOG.debug(f"Plan ID returned from CLI: {self.plan_id}")
                if self.plan_id:
                    reporting.add_test_step("Create Migration Plan", tvaultconf.PASS)
                else:
                    raise Exception("Create Migration Plan")
            else:
                raise Exception("Execute migration-plan-create CLI command")

            #DB verification
            self.wait_for_migrationplan_tobe_available(self.plan_id)
            self.plan_db = query_data.get_migration_plan(self.plan_id)
            LOG.debug(f"Plan details from DB: {self.plan_db}")
            if self.plan_db[0] == tvaultconf.migration_plan_name and \
                self.plan_db[1] == "available":
                reporting.add_test_step("DB verification", tvaultconf.PASS)
            else:
                raise Exception("DB verification")

            cli_err = cli_parser.cli_error(mp_create)
            LOG.debug("cli error: {}".format(cli_err))
            if (cli_err and cli_error_str in cli_err):
                reporting.add_test_step(
                    "Proper error message for migration plan create if VM already part of any migration plan", tvaultconf.PASS)
                LOG.debug("Command executed correctly")
            else:
                reporting.add_test_step(
                    "Proper error message for migration plan create if VM already part of any migration plan", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            self.plan_id_1 = query_data.get_last_created_migration_planid()[0]
            LOG.debug(f"Latest migration plan id from DB: {self.plan_id_1}")
            if self.plan_id != self.plan_id_1:
                LOG.error("New migration plan created")
                self.plan_db_1 = query_data.get_migration_plan(self.plan_id_1)
                LOG.debug(f"self.plan_db_1: {self.plan_db_1}")
                if self.plan_db_1[0] == tvaultconf.migration_plan_name:
                    reporting.add_test_step(f"New migration plan got created with status {self.plan_db_1[1]}", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)

            #Delete migration plan
            self.delete_migration_plan(self.plan_id)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_03_migration(self):
        try:
            reporting.add_test_script(str(__name__) + \
                    "_list_migration_plans_api")
            self.vms = self.get_migration_test_vms(vm_list= \
                            self.get_vcenter_vms())
            self.plan_id, self.err_str = self.create_migration_plan(self.vms)
            LOG.debug(f"Plan ID returned from API: {self.plan_id}")
            LOG.error(f"Error: {self.err_str}")
            if self.plan_id:
                reporting.add_test_step("Create Migration Plan", tvaultconf.PASS)
            else:
                raise Exception("Create Migration Plan")

            self.wait_for_migrationplan_tobe_available(self.plan_id)
            self.plans_db = query_data.get_migration_plans()
            LOG.debug(f"Migration plans from DB: {self.plans_db}")

            self.plans_api = self.getMigrationPlansList()
            LOG.debug(f"Migration plans from API: {self.plans_api}")

            if self.plans_db.sort() == self.plans_api.sort():
                reporting.add_test_step("DB verification", tvaultconf.PASS)
            else:
                raise Exception("DB verification")

        except Exception as e:
            LOG.error(f"Exception: {e}")
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_04_migration(self):
        try:
            reporting.add_test_script(str(__name__) + \
                    "_list_migration_plans_cli")
            self.vms = self.get_migration_test_vms(vm_list= \
                            self.get_vcenter_vms())
            self.plan_id, self.err_str = self.create_migration_plan(self.vms)
            LOG.debug(f"Plan ID returned from API: {self.plan_id}")
            LOG.error(f"Error: {self.err_str}")
            if self.plan_id:
                reporting.add_test_step("Create Migration Plan", tvaultconf.PASS)
            else:
                raise Exception("Create Migration Plan")

            self.wait_for_migrationplan_tobe_available(self.plan_id)
            self.plans_db = query_data.get_migration_plans()
            LOG.debug(f"Migration plans from DB: {self.plans_db}")

            out = cli_parser.cli_output(command_argument_string.migration_plan_list)
            self.plans_cli = [x['ID'] for x in json.loads(out)]
            LOG.debug(f"Migration plans from CLI: {self.plans_cli}")

            if self.plans_db.sort() == self.plans_cli.sort():
                reporting.add_test_step("DB verification", tvaultconf.PASS)
            else:
                raise Exception("DB verification")

            os.environ['OS_PROJECT_NAME'] = CONF.identity.project_alt_name
            vm_str = ""
            for vm in self.vms:
                vm_str += " " + vm

            mp_create = command_argument_string.migration_plan_create +\
                    vm_str
            out = cli_parser.cli_output(mp_create)
            if out:
                self.plan_id_1 = json.loads(out)[0]['ID']
                LOG.debug(f"Plan ID returned from CLI: {self.plan_id_1}")
                if self.plan_id_1:
                    reporting.add_test_step("Create Migration Plan on other project", tvaultconf.PASS)
                else:
                    raise Exception("Create Migration Plan on other project")
            else:
                raise Exception("Execute migration-plan-create CLI command on other project")

            os.environ['OS_PROJECT_NAME'] = CONF.identity.project_name
            self.cmd_1 = command_argument_string.migration_plan_list + " --all True"
            out = cli_parser.cli_output(self.cmd_1)
            LOG.debug(f"CLI response for migration plan list with all True: {out}")
            self.plans_cli = [x['ID'] for x in json.loads(out)]
            LOG.debug(f"Migration plans from CLI: {self.plans_cli}")

            if self.plan_id_1 in self.plans_cli:
                LOG.debug("Migration plan of other project listed in CLI")
                reporting.add_test_step("Migration plan list with --all True option", tvaultconf.PASS)
            else:
                LOG.error("Migration plan of other project not listed in CLI")
                reporting.add_test_step("Migration plan list with --all True option", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            self.cmd_1 = command_argument_string.migration_plan_list + " --all False"
            out = cli_parser.cli_output(self.cmd_1)
            LOG.debug(f"CLI response for migration plan list with all True: {out}")
            self.plans_cli = [x['ID'] for x in json.loads(out)]
            LOG.debug(f"Migration plans from CLI: {self.plans_cli}")

            if self.plan_id_1 not in self.plans_cli:
                LOG.debug("Migration plan of other project not listed in CLI")
                reporting.add_test_step("Migration plan list with --all False option", tvaultconf.PASS)
            else:
                LOG.error("Migration plan of other project listed in CLI")
                reporting.add_test_step("Migration plan list with --all False option", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            #cleanup migration plan on other project
            self.delete_migration_plan(self.plan_id_1)

        except Exception as e:
            LOG.error(f"Exception: {e}")
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_05_migration(self):
        try:
            reporting.add_test_script(str(__name__) + \
                    "_delete_migration_plan_api")
            self.vms = self.get_migration_test_vms(vm_list= \
                            self.get_vcenter_vms())
            self.plan_id, self.err_str = self.create_migration_plan(self.vms)
            LOG.debug(f"Plan ID returned from API: {self.plan_id}")
            LOG.error(f"Error: {self.err_str}")
            if self.plan_id:
                reporting.add_test_step("Create Migration Plan", tvaultconf.PASS)
            else:
                raise Exception("Create Migration Plan")

            #Delete migration plan
            self.plan_delete = self.delete_migration_plan(self.plan_id)
            if self.plan_delete:
                reporting.add_test_step("Delete migration plan", tvaultconf.PASS)
            else:
                reporting.add_test_step("Delete migration plan", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            #DB verification
            self.plan_db = query_data.get_migration_plan(self.plan_id)
            LOG.debug(f"Plan details from DB: {self.plan_db}")
            if self.plan_db is None:
                reporting.add_test_step("DB verification", tvaultconf.PASS)
            else:
                reporting.add_test_step("DB verification", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_06_migration(self):
        try:
            reporting.add_test_script(str(__name__) + \
                    "_delete_migration_plan_cli")
            self.vms = self.get_migration_test_vms(vm_list= \
                            self.get_vcenter_vms())
            self.plan_id, self.err_str = self.create_migration_plan(self.vms)
            LOG.debug(f"Plan ID returned from API: {self.plan_id}")
            LOG.error(f"Error: {self.err_str}")
            if self.plan_id:
                reporting.add_test_step("Create Migration Plan", tvaultconf.PASS)
            else:
                raise Exception("Create Migration Plan")

            #Delete migration plan
            mp_delete = command_argument_string.migration_plan_delete + self.plan_id
            rc = cli_parser.cli_returncode(mp_delete)
            if rc != 0:
                reporting.add_test_step(
                    "Execute migration-plan-delete command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute migration-plan-delete command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            #DB verification
            self.plan_db = query_data.get_migration_plan(self.plan_id)
            LOG.debug(f"Plan details from DB: {self.plan_db}")
            if self.plan_db is None:
                reporting.add_test_step("DB verification", tvaultconf.PASS)
            else:
                reporting.add_test_step("DB verification", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_07_migration(self):
        try:
            reporting.add_test_script(str(__name__) + \
                    "_show_migration_plan_api")
            self.vms = self.get_migration_test_vms(vm_list= \
                            self.get_vcenter_vms())
            self.plan_id, self.err_str = self.create_migration_plan(self.vms)
            LOG.debug(f"Plan ID returned from API: {self.plan_id}")
            LOG.error(f"Error: {self.err_str}")
            if self.plan_id:
                reporting.add_test_step("Create Migration Plan", tvaultconf.PASS)
            else:
                raise Exception("Create Migration Plan")

            self.plan_api = self.getMigrationPlanDetails(self.plan_id)
            self.plan_api_vms = [x['id'] for x in self.plan_api['vms']]
            if self.plan_api['id'] == self.plan_id and \
                self.plan_api['name'] == tvaultconf.migration_plan_name and \
                self.plan_api['description'] == tvaultconf.migration_plan_desc and\
                self.plan_api_vms.sort() == self.vms.sort() and\
                self.plan_api['status'] == 'available':
                reporting.add_test_step("Verification", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verification", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_08_migration(self):
        try:
            reporting.add_test_script(str(__name__) + \
                    "_show_migration_plan_cli")
            self.vms = self.get_migration_test_vms(vm_list= \
                            self.get_vcenter_vms())
            self.plan_id, self.err_str = self.create_migration_plan(self.vms)
            LOG.debug(f"Plan ID returned from API: {self.plan_id}")
            LOG.error(f"Error: {self.err_str}")
            if self.plan_id:
                reporting.add_test_step("Create Migration Plan", tvaultconf.PASS)
            else:
                raise Exception("Create Migration Plan")

            #Show migration plan
            mp_show = command_argument_string.migration_plan_show + self.plan_id
            out = cli_parser.cli_output(mp_show)
            LOG.debug(f"CLI response for migration plan show: {out}")

            #DB verification
            self.plan_db = query_data.get_migration_plan_details(self.plan_id)
            self.plan_vms_db = query_data.get_migration_plan_vms(self.plan_id)
            LOG.debug(f"Plan details from DB: {self.plan_db}, VMs from DB: {self.plan_vms_db}")
            if self.plan_db[0] == self.plan_id and \
                self.plan_db[1] == tvaultconf.migration_plan_name and \
                self.plan_db[2] == tvaultconf.migration_plan_desc and\
                self.plan_vms_db.sort() == self.vms.sort() and\
                self.plan_db[3] == 'available':
                reporting.add_test_step("DB verification", tvaultconf.PASS)
            else:
                reporting.add_test_step("DB verification", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_09_migration(self):
        try:
            reporting.add_test_script(str(__name__) + \
                    "_discover_vms_api")
            self.vms = self.get_migration_test_vms(vm_list= \
                            self.get_vcenter_vms())
            self.plan_id, self.err_str = self.create_migration_plan(self.vms)
            LOG.debug(f"Plan ID returned from API: {self.plan_id}")
            LOG.error(f"Error: {self.err_str}")
            if self.plan_id:
                reporting.add_test_step("Create Migration Plan", tvaultconf.PASS)
            else:
                raise Exception("Create Migration Plan")

            self.err_str = self.discover_vms(self.plan_id)
            if self.err_str:
                reporting.add_test_step("Discover VMs", tvaultconf.PASS)
            else:
                raise Exception("Discover VMs")

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_10_migration(self):
        try:
            reporting.add_test_script(str(__name__) + \
                    "_discover_vms_cli")
            self.vms = self.get_migration_test_vms(vm_list= \
                            self.get_vcenter_vms())
            self.plan_id, self.err_str = self.create_migration_plan(self.vms)
            LOG.debug(f"Plan ID returned from API: {self.plan_id}")
            LOG.error(f"Error: {self.err_str}")
            if self.plan_id:
                reporting.add_test_step("Create Migration Plan", tvaultconf.PASS)
            else:
                raise Exception("Create Migration Plan")

            #Discover VMs
            discover_vms = command_argument_string.migration_discover_vms + self.plan_id
            out = cli_parser.cli_output(discover_vms)
            LOG.debug(f"CLI response for discover vms: {out}")

            #Verification
            if out.find(tvaultconf.discover_success_str) != -1:
                reporting.add_test_step("Discover VMs Verification", tvaultconf.PASS)
            else:
                reporting.add_test_step("Discover VMs Verification", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

