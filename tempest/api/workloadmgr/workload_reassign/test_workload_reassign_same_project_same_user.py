import os
import sys

from oslo_log import log as logging

from tempest import config
from tempest import reporting
from tempest import tvaultconf
from tempest.api.workloadmgr import base
from tempest.lib import decorators

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
    @decorators.attr(type='workloadmgr_api')
    def test_workload_reassign_same_project_same_user(self):
        try:

            tests = [['tempest.api.workloadmgr.workload_reassignment.create_workload',
                      0],
                     ['tempest.api.workloadmgr.workload_reassignment.assign_another_user_and_project',
                      0],
                     ['tempest.api.workloadmgr.workload_reassignment.reassign_same_user_and_project',
                      0]]

            reporting.add_test_script(tests[0][0])

            ### Create vm and workload ###
            LOG.debug("Create VM")

            self.created = False
            vm_id = self.create_vm(vm_cleanup=True)
            LOG.debug("\nVm id : {}\n".format(str(vm_id)))

            LOG.debug("Create workload")
            workload_id = self.workload_create(
                [vm_id], tvaultconf.parallel, workload_cleanup=True)
            LOG.debug("Workload ID: " + str(workload_id))

            if(workload_id is not None):
                self.wait_for_workload_tobe_available(workload_id)
                if(self.getWorkloadStatus(workload_id) == "available"):
                    reporting.add_test_step("Create workload", tvaultconf.PASS)
                    tests[0][1] = 1
                else:
                    reporting.add_test_step("Create workload", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Create workload", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)


            reporting.add_test_script(tests[1][0])
            LOG.debug("Assign project and user")
            ### create project1 and user1 
            tenant_id = CONF.identity.tenant_id
            user_id = CONF.identity.user_id
            LOG.debug(f"tenant_id {tenant_id} and user_id {user_id}")
            rc = self.workload_reassign(tenant_id, workload_id, user_id)
            if rc == 0:
                LOG.debug("Workload reassign from tenant 1 to tenant 1 passed")
                reporting.add_test_step(
                    "Workload reassign from tenant 1 to 1", tvaultconf.PASS)
                tests[1][1] = 1
            else:
                LOG.error("Workload reassign from tenant 1 to 1 failed")
                reporting.add_test_step(
                    "Workload reassign from tenant 1 to 1", tvaultconf.FAIL)


            reporting.add_test_script(tests[2][0])
            LOG.debug("Assign project and user again")
            #reassign the same user and project to the workload.     
            rc = self.workload_reassign(tenant_id, workload_id, user_id)
            if rc == 0:
                LOG.debug("Workload reassign from tenant 1 to tenant 1 passed")
                reporting.add_test_step(
                    "Workload reassign from tenant 1 to 1", tvaultconf.PASS)
                tests[2][1] = 1
            else:
                LOG.error("Workload reassign from tenant 1 to 1 failed")
                reporting.add_test_step(
                    "Workload reassign from tenant 1 to 1", tvaultconf.FAIL)


            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()


