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
                LOG.debug(f"Plan ID returned from API: {self.plan_id}")
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
