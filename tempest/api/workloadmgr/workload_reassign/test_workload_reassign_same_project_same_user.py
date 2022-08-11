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

            reporting.add_test_script(str(__name__))

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
            else:
                LOG.error("Full snapshot creation failed.")
                raise Exception("Create full snapshot")


            #workload reassignment of same user and same tenant.
            rc = self.workload_reassign(CONF.identity.tenant_id, workload_id, CONF.identity.user_id)
            if rc == 0:
                LOG.debug("Workload reassign to same user and same tenant is passed")
                reporting.add_test_step(
                    "Workload reassign to same user and same tenant", tvaultconf.PASS)
            else:
                LOG.error("Workload reassign to same user and same tenant is failed")
                raise Exception("Workload reassign to same user and same tenant")


        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()




