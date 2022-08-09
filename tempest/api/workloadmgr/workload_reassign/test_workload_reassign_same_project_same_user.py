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

    def create_snapshot(self, workload_id, is_full=True):
        if is_full:
            substitution = 'Full'
        else:
            substitution = 'Incremental'

        snapshot_id, command_execution, snapshot_execution = self.workload_snapshot_cli(
            workload_id, is_full=is_full)
        if command_execution == 'pass':
            reporting.add_test_step("{} snapshot command execution".format(
                substitution), tvaultconf.PASS)
            LOG.debug("Command executed correctly for full snapshot")
        else:
            reporting.add_test_step("{} snapshot command execution".format(
                substitution), tvaultconf.FAIL)
            raise Exception(
                "Command did not execute correctly for full snapshot")

        if snapshot_execution == 'pass':
            reporting.add_test_step("{} snapshot".format(
                substitution), tvaultconf.PASS)
        else:
            reporting.add_test_step("{} snapshot".format(
                substitution), tvaultconf.FAIL)
            raise Exception("Full snapshot failed")

        return (snapshot_id)


    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    @decorators.attr(type='workloadmgr_api')
    def test_workload_reassign_same_project_same_user(self):
        try:

            tests = [['tempest.api.workloadmgr.workload_reassignment.create_workload_and_snapshot',
                      0],
                     ['tempest.api.workloadmgr.workload_reassignment.assign_tenant1_and_user1',
                      0],
                     ['tempest.api.workloadmgr.workload_reassignment.reassign_same_tenant1_and_user1',
                      0]]

            reporting.add_test_script(tests[0][0])

            ### Create vm and workload ###
            LOG.debug("Create VM")

            self.created = False
            vm_id = self.create_vm(vm_cleanup=True)
            LOG.debug("\nVm id : {}\n".format(str(vm_id)))

            #Create the trust
            trust_id = self.create_trust(tvaultconf.trustee_role)
            if trust_id:
                reporting.add_test_step("Create user trust on project", tvaultconf.PASS)
            else:
                LOG.error("Create user trust on project failed.")
                raise Exception("Create user trust on project")

            LOG.debug("Create workload")
            workload_id = self.workload_create(
                [vm_id], tvaultconf.parallel, workload_cleanup=True)
            LOG.debug("Workload ID: " + str(workload_id))

            if(workload_id is not None):
                self.wait_for_workload_tobe_available(workload_id)
                if(self.getWorkloadStatus(workload_id) == "available"):
                    reporting.add_test_step("Create workload", tvaultconf.PASS)
                else:
                    LOG.error("Failed to get workload status as available for workload ID: " + str(workload_id))
                    raise Exception("Create workload")
            else:
                LOG.error("Failed to create workload.")
                raise Exception("Create workload")

            #take a full snapshot of it.
            snapshot_id = self.create_snapshot(workload_id, is_full=True)

            self.wait_for_workload_tobe_available(workload_id)
            snapshot_status = self.getSnapshotStatus(workload_id, snapshot_id)

            if (snapshot_status == "available"):
                LOG.debug("Full snapshot created.")
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                tests[0][1] = 1
            else:
                LOG.error("Full snapshot creation failed.")
                raise Exception("Create full snapshot")


            #assign tenant1 and user1 to workload created.
            reporting.test_case_to_write()
            reporting.add_test_script(tests[1][0])
            LOG.debug("Assign tenant and user to workload ID: " + str(workload_id))

            ### copy tenant1 and user1
            tenant_id = CONF.identity.tenant_id
            user_id = CONF.identity.user_id

            LOG.debug(f"tenant_id {tenant_id} and user_id {user_id}")

            rc = self.workload_reassign(tenant_id, workload_id, user_id)
            if rc == 0:
                LOG.debug("Workload reassign to tenant 1 passed")
                reporting.add_test_step(
                    "Workload reassign to tenant 1", tvaultconf.PASS)
                tests[1][1] = 1
            else:
                LOG.error("Workload reassign to tenant 1 failed")
                raise Exception("Workload reassign to tenant 1")


            #assign tenant1 and user1 to the same workload again.
            reporting.test_case_to_write()
            reporting.add_test_script(tests[2][0])
            LOG.debug("Reassign tenant-1 and user-1 to workload ID: " + str(workload_id))

            #reassign the same user and project to the workload.
            rc = self.workload_reassign(tenant_id, workload_id, user_id)
            if rc == 0:
                LOG.debug("Workload reassign from tenant 1 to tenant 1 passed")
                reporting.add_test_step(
                    "Workload reassign from tenant 1 to tenant 1", tvaultconf.PASS)
                tests[2][1] = 1
            else:
                LOG.error("Workload reassign from tenant 1 to tenant 1 failed")
                raise Exception("Workload reassign from tenant 1 to tenant 1")


            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

        finally:
            for test in tests:
                if test[1] != 1:
                    reporting.add_test_script(test[0])
                    reporting.set_test_script_status(tvaultconf.FAIL)
                    reporting.test_case_to_write()



