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

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    @test.pre_req({'type': 'small_workload'})
    @decorators.attr(type='workloadmgr_cli')
    def test_1_trust(self):
        try:
            reporting.add_test_script(str(__name__) + \
                    "_validate_scheduler_trust_with_scheduler_enabled")
            if self.exception != "":
                LOG.error("pre req failed")
                raise Exception(str(self.exception))
            LOG.debug("pre req completed")
            global vm_id
            global volume_id
            vm_id = self.vm_id
            volume_id = self.volume_id

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
            try:
                cmd = command_argument_string.workload_scheduler_trust_check +\
                            self.wid
                resp = eval(cli_parser.cli_output(cmd))
                reporting.add_test_step("Execute scheduler-trust-validate CLI",
                        tvaultconf.PASS)
                wlm_trust = resp['trust']
                wlm_trust_valid = resp['is_valid']
            except Exception as e:
                LOG.error(f"Exception in scheduler-trust-validate CLI: {e}")
                raise Exception("Execute scheduler-trust-validate CLI")

            #Fetch trust list from API
            trust_list = self.get_trusts()

            #Verify if trust details returned in steps 3 and 4 match
            found = False
            for trust in trust_list:
                if trust['name'] == wlm_trust['name']:
                    found = True
                    break
            if found and wlm_trust_valid:
                reporting.add_test_step("Verify valid trust", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify valid trust", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            #Delete the trust using API
            if self.delete_trust(wlm_trust['name']):
                reporting.add_test_step("Delete trust", tvaultconf.PASS)
            else:
                raise Exception("Delete trust")

            #Execute scheduler-trust-validate CLI for workload WL-1
            try:
                cmd = command_argument_string.workload_scheduler_trust_check +\
                            self.wid
                resp = eval(cli_parser.cli_output(cmd))
                reporting.add_test_step("Execute scheduler-trust-validate CLI",
                        tvaultconf.PASS)
                wlm_trust = resp['trust']
                wlm_trust_valid = resp['is_valid']
            except Exception as e:
                LOG.error(f"Exception in scheduler-trust-validate CLI: {e}")
                raise Exception("Execute scheduler-trust-validate CLI")

            #Verify if trust details are returned appropriately
            if not wlm_trust and not wlm_trust_valid:
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
            try:
                cmd = command_argument_string.workload_scheduler_trust_check +\
                            self.wid
                resp = eval(cli_parser.cli_output(cmd))
                reporting.add_test_step("Execute scheduler-trust-validate CLI",
                        tvaultconf.PASS)
                wlm_trust = resp['trust']
                wlm_trust_valid = resp['is_valid']
            except Exception as e:
                LOG.error(f"Exception in scheduler-trust-validate CLI: {e}")
                raise Exception("Execute scheduler-trust-validate CLI")

            #Verify if trust details are returned appropriately
            trust_list = self.get_trusts()
            found = False
            for trust in trust_list:
                if trust['name'] == wlm_trust['name']:
                    found = True
                    break
            if found and wlm_trust_valid:
                reporting.add_test_step("Verify valid trust", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify valid trust", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_3_cleanup(self):
        try:
            global vm_id
            global volume_id
            self.delete_vm(vm_id)
            self.delete_volume(volume_id)
        except Exception as e:
            LOG.error(f"Exception in test_3_cleanup: {e}")



