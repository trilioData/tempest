import os
import sys
import time
import json

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
    vm_id = None
    volume_id = None
    exception = ""
    trust_name = ""
    trust_list_db = []
    role_id = ""

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    def _execute_scheduler_trust_validate_cli(self):
        try:
            cmd = command_argument_string.workload_scheduler_trust_check +\
                    self.wid
            resp = eval(cli_parser.cli_output(cmd))
            reporting.add_test_step("Execute scheduler-trust-validate CLI",
                    tvaultconf.PASS)
            self.wlm_trust = resp['trust']
            self.wlm_trust_valid = resp['is_valid']
            self.wlm_scheduler = resp['scheduler_enabled']
        except Exception as e:
            LOG.error(f"Exception in scheduler-trust-validate CLI: {e}")
            raise Exception("Execute scheduler-trust-validate CLI")

    @decorators.attr(type='workloadmgr_cli')
    def test_1_trust_create(self):
        reporting.add_test_script(
                "tempest.api.workloadmgr.trust.test_trust_create")
        global trust_name
        global trust_list_db
        global role_id
        try:
            role_name = tvaultconf.test_role
            role_id = self.get_role_id(role_name)
            if len(role_id) != 1:
                raise Exception("Role ID not returned")
            if self.assign_role_to_user_project(CONF.identity.tenant_id,
                    CONF.identity.user_id, role_id[0], False):
                LOG.debug("Role assigned to user and project")
            else:
                raise Exception("Role assignment to user and project failed")

            cmd = command_argument_string.trust_create + role_name
            resp = eval(cli_parser.cli_output(cmd))
            LOG.debug(f"Response for trust-create: {resp}")
            reporting.add_test_step("Execute trust-create CLI",
                    tvaultconf.PASS)
            trust_name = resp['name']
            trust_list_db = query_data.get_trust_list(
                    CONF.identity.tenant_id, CONF.identity.user_id)
            LOG.debug(f"trust_list returned from DB: {trust_list_db}")
            if trust_name in trust_list_db:
                reporting.add_test_step("Verify trust created in DB",
                        tvaultconf.PASS)
            else:
                raise Exception("Verify trust created in DB")
        except Exception as e:
            LOG.error(f"Exception in test_1_trust_create: {e}")
            reporting.add_test_step(f"{e}", tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_2_trust_list(self):
        reporting.add_test_script(
                "tempest.api.workloadmgr.trust.test_trust_list")
        cmd = command_argument_string.trust_list
        global trust_list_db
        try:
            resp = eval(cli_parser.cli_output(cmd))
            LOG.debug(f"Response for trust-list: {resp}")
            reporting.add_test_step("Execute trust-list CLI",
                    tvaultconf.PASS)
            trust_list_cli = [tr['TrustID'] for tr in resp]

            LOG.debug(f"trust_list returned from CLI:{trust_list_cli}")
            LOG.debug(f"trust_list returned from DB:{trust_list_db}")
            if sorted(trust_list_cli) == sorted(trust_list_db):
                reporting.add_test_step("Verify trust list in DB and CLI",
                        tvaultconf.PASS)
            else:
                raise Exception("Verify trust list in DB and CLI")
        except Exception as e:
            LOG.error(f"Exception in test_2_trust_list: {e}")
            reporting.add_test_step(f"{e}", tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_3_trust_show(self):
        reporting.add_test_script(
                "tempest.api.workloadmgr.trust.test_trust_show")
        global trust_name
        cmd = command_argument_string.trust_show + trust_name
        try:
            resp = json.loads(cli_parser.cli_output(cmd))
            LOG.debug(f"Response for trust-show: {resp}")
            reporting.add_test_step("Execute trust-show CLI",
                    tvaultconf.PASS)
            trust_details_cli = []
            vars = ['version', 'user_id', 'project_id', 'name', 'value',
                    'description', 'status']
            for key in vars:
                trust_details_cli.append(resp[key])
            trust_details_cli.append(resp['metadata'][0]['value'])
            LOG.debug(f"trust details returned from CLI: {trust_details_cli}")
            trust_details_db = list(query_data.get_trust_details(trust_name))
            trust_details_db.append(tvaultconf.test_role)
            LOG.debug(f"trust details returned from DB: {trust_details_db}")
            if trust_details_db == trust_details_cli:
                reporting.add_test_step("Verify trust details in DB and CLI",
                        tvaultconf.PASS)
            else:
                raise Exception("Verify trust show in DB and CLI")
        except Exception as e:
            LOG.error(f"Exception in test_3_trust_show: {e}")
            reporting.add_test_step(f"{e}", tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_4_trust_delete(self):
        reporting.add_test_script(
                "tempest.api.workloadmgr.trust.test_trust_delete")
        global trust_name
        cmd = command_argument_string.trust_delete + trust_name
        try:
            rc = cli_parser.cli_returncode(cmd)
            if rc != 0:
                raise Exception("Execute trust-delete CLI")
            else:
                reporting.add_test_step("Execute trust-delete CLI",
                        tvaultconf.PASS)
            trust_list_db = query_data.get_trust_list(
                    CONF.identity.tenant_id, CONF.identity.user_id)
            LOG.debug(f"trust_list returned from DB: {trust_list_db}")
            if trust_name in trust_list_db:
                raise Exception("Trust still exists in DB")
            else:
                reporting.add_test_step("Verify trust deleted in DB",
                        tvaultconf.PASS)
        except Exception as e:
            LOG.error(f"Exception in test_4_trust_delete: {e}")
            reporting.add_test_step(f"{e}", tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @test.pre_req({'type': 'small_workload'})
    @decorators.attr(type='workloadmgr_cli')
    def test_5_trust(self):
        try:
            reporting.add_test_script(str(__name__) + \
                    "_validate_scheduler_trust_with_scheduler_enabled")
            if self.exception != "":
                LOG.error("pre req failed")
                raise Exception(str(self.exception))
            LOG.debug("pre req completed")
            global vm_id
            global volume_id
            global exception
            vm_id = self.vm_id
            volume_id = self.volume_id
            exception = self.exception

            # Create scheduled workload
            self.start_date = time.strftime("%m/%d/%Y")
            self.start_time = time.strftime("%I:%M %p")
            self.wid = self.workload_create([vm_id], tvaultconf.parallel,
                        jobschedule={"start_date": self.start_date,
                            "start_time": self.start_time,
                            "interval": tvaultconf.interval,
                            "retention_policy_type":
                                tvaultconf.retention_policy_type,
                            "retention_policy_value":
                                tvaultconf.retention_policy_value,
                            "enabled": "True"})
            LOG.debug("Workload ID: " + str(self.wid))
            self.wait_for_workload_tobe_available(self.wid)
            if(self.getWorkloadStatus(self.wid) == "available"):
                reporting.add_test_step(
                    "Create scheduled workload", tvaultconf.PASS)
            else:
                raise Exception("Create scheduled workload")

            #Execute scheduler-trust-validate CLI command
            self._execute_scheduler_trust_validate_cli()

            #Fetch trust list from API
            trust_list = self.get_trusts()

            #Verify if trust details returned in steps 3 and 4 match
            found = False
            for trust in trust_list:
                if trust['name'] == self.wlm_trust['name']:
                    found = True
                    break
            if found and self.wlm_trust_valid and self.wlm_scheduler:
                reporting.add_test_step("Verify valid trust", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify valid trust", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            #Delete the trust using API
            if self.delete_trust(self.wlm_trust['name']):
                reporting.add_test_step("Delete trust", tvaultconf.PASS)
            else:
                raise Exception("Delete trust")

            #Execute scheduler-trust-validate CLI for workload WL-1
            self._execute_scheduler_trust_validate_cli()

            #Verify if trust details are returned appropriately
            if not self.wlm_trust and not self.wlm_trust_valid and \
                    self.wlm_scheduler:
                reporting.add_test_step("Verify broken trust", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify broken trust", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            #Create the trust again using API
            trust_id = self.create_trust(tvaultconf.trustee_role)
            if trust_id:
                reporting.add_test_step("Create user trust on project", tvaultconf.PASS)
            else:
                raise Exception("Create user trust on project")

            #Execute scheduler-trust-validate CLI for workload WL-1
            self._execute_scheduler_trust_validate_cli()

            #Verify if trust details are returned appropriately
            trust_list = self.get_trusts()
            found = False
            for trust in trust_list:
                if trust['name'] == self.wlm_trust['name']:
                    found = True
                    break
            if found and self.wlm_trust_valid and self.wlm_scheduler:
                reporting.add_test_step("Verify valid trust", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify valid trust", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_6_trust(self):
        try:
            reporting.add_test_script(str(__name__) + \
                    "_validate_scheduler_trust_with_scheduler_disabled")
            global vm_id
            global volume_id
            global exception
            if exception != "":
                LOG.error("pre req failed")
                raise Exception(str(exception))
            LOG.debug("pre req completed")

            # Create workload with scheduler disabled using CLI
            workload_create = command_argument_string.workload_create + \
                " --instance instance-id=" + \
                str(vm_id) + " --jobschedule enabled=False"
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

            time.sleep(10)
            self.wid = query_data.get_workload_id_in_creation(tvaultconf.workload_name)
            LOG.debug("Workload ID: " + str(self.wid))
            if(self.wid is not None):
                self.wait_for_workload_tobe_available(self.wid)
                if(self.getWorkloadStatus(self.wid) == "available"):
                    reporting.add_test_step(
                        "Create workload with scheduler disable", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Create workload with scheduler disable", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                raise Exception("Create workload with scheduler disabled")

            #Execute scheduler-trust-validate CLI command
            self._execute_scheduler_trust_validate_cli()

            #Fetch trust list from API
            trust_list = self.get_trusts()

            #Verify trust details returned
            if not self.wlm_trust_valid and \
                    not self.wlm_scheduler and \
                    len(trust_list) > 0:
                reporting.add_test_step("Verify trust", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify trust", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            #Delete the trust using API
            if self.delete_trust(trust_list[0]['name']):
                reporting.add_test_step("Delete trust", tvaultconf.PASS)
            else:
                raise Exception("Delete trust")

            #Execute scheduler-trust-validate CLI for workload WL-1
            self._execute_scheduler_trust_validate_cli()

            #Verify if trust details are returned appropriately
            if not self.wlm_trust and \
                    not self.wlm_trust_valid and \
                    not self.wlm_scheduler:
                reporting.add_test_step("Verify trust", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify trust", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            #Create the trust again using API
            trust_id = self.create_trust(tvaultconf.trustee_role)
            if trust_id:
                reporting.add_test_step("Create user trust on project", tvaultconf.PASS)
            else:
                raise Exception("Create user trust on project")

        except Exception as e:
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            self.workload_delete(self.wid)
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_7_cleanup(self):
        try:
            global vm_id
            global volume_id
            global role_id
            self.delete_vm(vm_id)
            self.delete_volume(volume_id)
            self.remove_role_from_user_project(CONF.identity.tenant_id,
                    CONF.identity.user_id, role_id)
        except Exception as e:
            LOG.error(f"Exception in test_7_cleanup: {e}")

