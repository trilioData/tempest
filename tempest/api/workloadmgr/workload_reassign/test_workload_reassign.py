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


    @decorators.attr(type='workloadmgr_api')
    def test_01_workload_reassign(self):
        try:
            reporting.add_test_script(str(__name__) + "_different_user_different_tenant")
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


            #check if actually tenant id is changed for the workload or not. 
            workload_instance_info = self.get_workload_details(workload_id)
            LOG.debug(f"workload_instance teanant id={workload_instance_info['project_id']} and tempest conf tenant id={tenant_id_1}")
            if tenant_id_1 == workload_instance_info['project_id']:
                LOG.debug("Workload instance having correct tenant id. TEST CASE PASSED")
                reporting.add_test_step(
                    "tenant_id_1 workload reassign", tvaultconf.PASS)
            else:
                LOG.error("Workload instance showing different tenant id. TEST CASE FAILED")
                raise Exception("tenant_id_1 workload reassign")


            rc = self.workload_reassign(tenant_id, workload_id, user_id)
            if rc == 0:
                LOG.debug("Workload reassign from tenant 2 to tenant 1 passed")
                reporting.add_test_step(
                    "Workload reassign from tenant 2 to 1", tvaultconf.PASS)
            else:
                LOG.error("Workload reassign from tenant 2 to 1 failed")
                reporting.add_test_step(
                    "Workload reassign from tenant 2 to 1", tvaultconf.FAIL)

            #check if actually tenant id is changed for the workload or not. 
            workload_instance_info = self.get_workload_details(workload_id)
            LOG.debug(f"workload_instance teanant id={workload_instance_info['project_id']} and tempest conf tenant id={tenant_id}")
            if tenant_id == workload_instance_info['project_id']:
                LOG.debug("Workload instance having correct tenant id. TEST CASE PASSED")
                reporting.add_test_step(
                    "tenant_id workload reassign", tvaultconf.PASS)
            else:
                LOG.error("Workload instance showing different tenant id. TEST CASE FAILED")
                raise Exception("tenant_id workload reassign")


        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

        finally:
            reporting.test_case_to_write()

    '''
    OS-2058 - workload reassign with same user and same project.
    http://192.168.15.51/testlink/linkto.php?tprojectPrefix=OS&item=testcase&id=OS-2058
    '''
    @decorators.attr(type='workloadmgr_api')
    def test_02_workload_reassign(self):
        try:

            reporting.add_test_script(str(__name__) + "_same_user_same_tenant")

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

            #check if actually tenant id is changed for the workload or not. 
            workload_instance_info = self.get_workload_details(workload_id)
            LOG.debug(f"workload_instance teanant id={workload_instance_info['project_id']} and tempest conf tenant id={CONF.identity.tenant_id}")
            if CONF.identity.tenant_id == workload_instance_info['project_id']:
                LOG.debug("Workload instance having correct tenant id. TEST CASE PASSED")
                reporting.add_test_step(
                    "Same tenant workload reassign", tvaultconf.PASS)
            else:
                LOG.error("Workload instance showing different tenant id. TEST CASE FAILED")
                raise Exception("Same tenant workload reassign")

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()


    '''
    OS-2059 - workload reassign with same user and different project.
    http://192.168.15.51/testlink/linkto.php?tprojectPrefix=OS&item=testcase&id=OS-2059
    '''
    @decorators.attr(type='workloadmgr_api')
    def test_03_workload_reassign(self):
        try:

            reporting.add_test_script(str(__name__) + "_same_user_different_tenant")

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

            snapshot_status = self.getSnapshotStatus(workload_id, snapshot_id)

            if (snapshot_status == "available"):
                LOG.debug("Full snapshot created.")
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
            else:
                LOG.error("Full snapshot creation failed.")
                raise Exception("Create full snapshot")


            #use different project but same user and check the behavior.
            rc = self.workload_reassign(CONF.identity.tenant_id_1, workload_id, CONF.identity.user_id)
            if rc == 0:
                LOG.debug("Workload reassign to same user and different tenant is passed")
                reporting.add_test_step(
                    "Workload reassign to same user and different tenant", tvaultconf.PASS)
            else:
                LOG.error("Workload reassign to same user and different tenant is failed")
                raise Exception("Workload reassign to same user and different tenant")


            #check if actually tenant id is changed for the workload or not. 
            workload_instance_info = self.get_workload_details(workload_id)
            LOG.debug(f"workload_instance teanant id={workload_instance_info['project_id']} and tempest conf tenant id={CONF.identity.tenant_id_1}")
            if CONF.identity.tenant_id_1 == workload_instance_info['project_id']:
                LOG.debug("Workload instance having correct tenant id. TEST CASE PASSED")
                reporting.add_test_step(
                    "Different tenant workload reassign", tvaultconf.PASS)
            else:
                LOG.error("Workload instance showing different tenant id. TEST CASE FAILED")
                raise Exception("Different tenant workload reassign")

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()



