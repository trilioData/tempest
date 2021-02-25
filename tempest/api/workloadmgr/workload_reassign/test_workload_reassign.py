from tempest import reporting
from tempest import tvaultconf
from oslo_log import log as logging
from tempest.lib import decorators
from tempest import config
from tempest.api.workloadmgr import base
import sys
import os
sys.path.append(os.getcwd())

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()
        reporting.add_test_script(str(__name__))

    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_workload_reassign(self):
        try:
            ### Create vm and workload ###
            self.created = False
            vm_id = self.create_vm(vm_cleanup=True)
            LOG.debug("\nVm id : {}\n".format(str(vm_id)))
            vmdetails = self.get_vm_details(vm_id)
            workload_id = self.workload_create(
                [vm_id], tvaultconf.parallel, workload_cleanup=True)
            LOG.debug("Workload ID: " + str(workload_id))
            if(workload_id is not None):
                self.wait_for_workload_tobe_available(workload_id)
                if(self.getWorkloadStatus(workload_id) == "available"):
                    reporting.add_test_step("Create workload", tvaultconf.PASS)
                else:
                    reporting.add_test_step("Create workload", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Create workload", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            tenant_id = CONF.identity.tenant_id
            tenant_id_1 = CONF.identity.tenant_id_1

            user_id = CONF.identity.user_id
            user_id_1 = CONF.identity.user_id_1

            rc = self.workload_reassign(tenant_id_1, workload_id, user_id_1)
            if rc == 0:
                LOG.debug("Workload reassign from tenant 1 to tenant 2 passed")
                reporting.add_test_step(
                    "Workload reassign from tenant 1 to 2", tvaultconf.PASS)
            else:
                LOG.error("Workload reassign from tenant 1 to 2 failed")
                reporting.add_test_step(
                    "Workload reassign from tenant 1 to 2", tvaultconf.FAIL)

            rc = self.workload_reassign(tenant_id, workload_id, user_id)
            if rc == 0:
                LOG.debug("Workload reassign from tenant 2 to tenant 1 passed")
                reporting.add_test_step(
                    "Workload reassign from tenant 2 to 1", tvaultconf.PASS)
            else:
                LOG.error("Workload reassign from tenant 2 to 1 failed")
                reporting.add_test_step(
                    "Workload reassign from tenant 2 to 1", tvaultconf.FAIL)
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
