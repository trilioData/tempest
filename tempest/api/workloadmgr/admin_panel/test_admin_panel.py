import os
import sys

from oslo_log import log as logging

from tempest import config
from tempest import reporting
from tempest import test
from tempest import tvaultconf
from tempest.api.workloadmgr import base
from tempest.lib import decorators

sys.path.append(os.getcwd())

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']
    workload_id = None
    snapshot_id = None
    vm_id = None
    volume_id = None
    workload_name = None

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    @test.pre_req({'type': 'basic_workload'})
    @decorators.attr(type='smoke')
    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    @decorators.attr(type='workloadmgr_api')
    def test_1_get_audit_log(self):
        try:
            reporting.add_test_script(str(__name__) + "_get_audit_log")
            if self.exception != "":
                LOG.debug("pre req failed")
                reporting.add_test_step(str(self.exception), tvaultconf.FAIL)
                raise Exception(str(self.exception))

            global vm_id
            global volume_id
            global workload_id
            global workload_name
            global snapshot_id

            workload_id = self.wid
            workload_name = self.workload_name
            vm_id = self.vm_id
            volume_id = self.volume_id

            LOG.debug("workload is:" + str(workload_id))
            LOG.debug("workload is:" + str(workload_name))
            LOG.debug("vm id: " + str(vm_id))
            LOG.debug("volume id: " + str(volume_id))

            snapshot_id = self.workload_snapshot(workload_id, True)

            wc = self.wait_for_snapshot_tobe_available(
                workload_id, snapshot_id)
            if (str(wc) == "available"):
                reporting.add_test_step("Full snapshot", tvaultconf.PASS)
                LOG.debug("Workload snapshot successfully completed")
                self.created = True
            else:
                if (str(wc) == "error"):
                    pass
            if (self.created == False):
                reporting.add_test_step("Full snapshot", tvaultconf.FAIL)
                raise Exception("Workload snapshot did not get created")

            audit_log = self.getAuditLog()
            LOG.debug("Audit logs are : " + str(audit_log))
            wkld_name = tvaultconf.workload_name
            if len(audit_log) >= 0 and str(audit_log).find(wkld_name):
                LOG.debug("audit log API returns log successfully")
                reporting.add_test_step("Audit Log", tvaultconf.PASS)
            else:
                LOG.debug("audit log API does not return anything")
                reporting.add_test_step("Audit Log", tvaultconf.FAIL)

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    @decorators.attr(type='workloadmgr_api')
    def test_2_get_storage_details(self):
        try:
            reporting.add_test_script(str(__name__) + "_get_storage_details")

            storage_usage = self.getStorageUsage()
            LOG.debug("Storage details are : " + str(storage_usage))
            wkld_name = workload_name
            if len(
                storage_usage) > 0 and storage_usage[0]['total_capacity_humanized'] is not None:
                LOG.debug("storage details returns successfully")
                reporting.add_test_step("Storage Details ", tvaultconf.PASS)
            else:
                LOG.debug("storage detailsAPI does not return anything")
                reporting.add_test_step("Storage Details", tvaultconf.FAIL)

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    @decorators.attr(type='workloadmgr_api')
    def test_3_get_tenant_details(self):
        try:
            reporting.add_test_script(str(__name__) + "_get_tenant_details")

            tenant_usage = self.getTenantUsage()
            LOG.debug("Tenant details are : " + str(tenant_usage))
            wkld_name = workload_name
            if len(tenant_usage) > 0:
                LOG.debug("Tenant details returns successfully")
                reporting.add_test_step("Tenant Details ", tvaultconf.PASS)
            else:
                LOG.debug("Tenant details API does not return anything")
                reporting.add_test_step("Tenant Details", tvaultconf.FAIL)

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_4_wlm_service(self):
        try:
            reporting.add_test_script(str(__name__) + "_disable_enable_wlm_service")
            wlm_nodes = self.get_wlm_nodes()
            node_names = [x['node'] for x in wlm_nodes]
            LOG.debug(f"node_names: {node_names}")

            wlm_disable = command_argument_string.service_disable +\
                    node_names[0]
            out = (cli_parser.cli_output(wlm_disable)).replace('\n', '')
            LOG.debug(f"CLI output: {out}")

            expected_resp = tvaultconf.service_disable_msg + node_names[0]
            if out == expected_resp:
                reporting.add_test_step("Disable WLM service", tvaultconf.PASS)
            else:
                reporting.add_test_step("Disable WLM service", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            db_data = query_data.get_service_status(node_names[0])
            LOG.debug(f"Data returned from DB: {db_data}")
            if db_data[0] == 1 and \
                    db_data[1].find(tvaultconf.wlm_disable_reason) != -1:
                reporting.add_test_step("Verification with DB", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verification with DB", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            wlm_nodes = self.get_wlm_nodes()
            for node in wlm_nodes:
                if node['node'] == node_names[0]:
                    if node['status'] == 'Down':
                        reporting.add_test_step("Node status verification", tvaultconf.PASS)
                    else:
                        reporting.add_test_step("Node status verification", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)
                    break

            wlm_enable = command_argument_string.service_enable +\
                    node_names[0]
            out = (cli_parser.cli_output(wlm_enable)).replace('\n', '')
            LOG.debug(f"CLI output: {out}")

            expected_resp = tvaultconf.service_enable_msg + node_names[0]
            if out == expected_resp:
                reporting.add_test_step("Enable WLM service", tvaultconf.PASS)
            else:
                reporting.add_test_step("Enable WLM service", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            db_data = query_data.get_service_status(node_names[0])
            LOG.debug(f"Data returned from DB: {db_data}")
            if db_data[0] == 0 and not db_data[1]:
                reporting.add_test_step("Verification with DB", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verification with DB", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            wlm_nodes = self.get_wlm_nodes()
            for node in wlm_nodes:
                if node['node'] == node_names[0]:
                    if node['status'] == 'Up':
                        reporting.add_test_step("Node status verification", tvaultconf.PASS)
                    else:
                        reporting.add_test_step("Node status verification", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)
                    break

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()



