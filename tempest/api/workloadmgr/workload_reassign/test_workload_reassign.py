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

            self.created = False
            vm_id = self.create_vm(vm_cleanup=True)
            LOG.debug("\nVm id : {}\n".format(str(vm_id)))

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

            self.created = False
            vm_id = self.create_vm(vm_cleanup=True)
            LOG.debug("\nVm id : {}\n".format(str(vm_id)))

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




    '''
    OS-2061 - workload reassign with temp user and same project after deletion of temp user.
    http://192.168.15.51/testlink/linkto.php?tprojectPrefix=OS&item=testcase&id=OS-2061
    '''
    @decorators.attr(type='workloadmgr_api')
    def test_04_workload_reassign(self):
        try:

            reporting.add_test_script(str(__name__) + "_same_user_same_tenant_after_deletion_of_user")

            #create a temp user...
            self.temp_user_id = self.createUser()

            #assign trustee role
            role_id = self.get_role_id(tvaultconf.trustee_role)
            if len(role_id) != 1:
                raise Exception("Role ID not returned")

            #assign role to user and current project.
            if self.assign_role_to_user_project(CONF.identity.tenant_id,
                    self.temp_user_id, role_id[0], False):
                LOG.debug("Role assigned to user and project")
                reporting.add_test_step("Role assignment to user and project", tvaultconf.PASS)
            else:
                raise Exception("Role assignment to user and project failed")

            ### Create vm and workload ###
            self.created = False
            vm_id = self.create_vm(vm_cleanup=True)
            LOG.debug("\nVm id : {}\n".format(str(vm_id)))


            ### create workload ###
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


            #use temp user for workload reassign.
            rc = self.workload_reassign(CONF.identity.tenant_id, workload_id, self.temp_user_id)
            if rc == 0:
                LOG.debug("Workload reassign to same project with temp user is passed")
                reporting.add_test_step(
                    "Workload reassign to same project with temp user", tvaultconf.PASS)
            else:
                LOG.error("Workload reassign to same project with temp user is failed")
                raise Exception("Workload reassign to same project with temp user")

            #delete the current created user.
            resp = self.deleteUser(self.temp_user_id)
            if resp:
                LOG.debug(f"User {self.temp_user_id} deleted successfully")
                reporting.add_test_step(
                    "User deletion", tvaultconf.PASS)
            else:
                LOG.error(f"User {self.temp_user_id} is not deleted successfully")
                raise Exception("User deletion")

            #use same deleted temp user for workload reassign.
            rc = self.workload_reassign(CONF.identity.tenant_id, workload_id, self.temp_user_id)
            if rc == 0:
                LOG.error("Workload reassign with deleted temp user is successful. Test case failed.")
                raise Exception("Workload reassign with deleted temp user")
            else:
                LOG.debug("Workload reassign with deleted temp user is failed. Test case is passed.")
                reporting.add_test_step(
                    "Workload reassign with deleted temp user", tvaultconf.PASS)


        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()




    '''
    OS-2062 - workload reassign with different user and same project after deletion of temp user.
    http://192.168.15.51/testlink/linkto.php?tprojectPrefix=OS&item=testcase&id=OS-2062
    '''
    @decorators.attr(type='workloadmgr_api')
    def test_05_workload_reassign(self):
        try:

            reporting.add_test_script(str(__name__) + "_different_user_same_tenant_after_deletion_of_user1")

            #create a temp user...
            self.temp_user_id = self.createUser()

            #assign trustee role
            role_id = self.get_role_id(tvaultconf.trustee_role)
            if len(role_id) != 1:
                raise Exception("Role ID not returned")

            #assign role to user and current project.
            if self.assign_role_to_user_project(CONF.identity.tenant_id,
                    self.temp_user_id, role_id[0], False):
                LOG.debug("Role assigned to user and project")
                reporting.add_test_step("Role assignment to user and project", tvaultconf.PASS)
            else:
                raise Exception("Role assignment to user and project failed")

            ### Create vm and workload ###
            self.created = False
            vm_id = self.create_vm(vm_cleanup=True)
            LOG.debug("\nVm id : {}\n".format(str(vm_id)))


            ### create workload ###
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


            #use temp user for workload reassign.
            rc = self.workload_reassign(CONF.identity.tenant_id, workload_id, self.temp_user_id)
            if rc == 0:
                LOG.debug("Workload reassign to same project with temp user is passed")
                reporting.add_test_step(
                    "Workload reassign to same project with temp user", tvaultconf.PASS)
            else:
                LOG.error("Workload reassign to same project with temp user is failed")
                raise Exception("Workload reassign to same project with temp user")

            #delete the current created user.
            resp = self.deleteUser(self.temp_user_id)
            if resp:
                LOG.debug(f"User {self.temp_user_id} deleted successfully")
                reporting.add_test_step(
                    "User deletion", tvaultconf.PASS)
            else:
                LOG.error(f"User {self.temp_user_id} is not deleted successfully")
                raise Exception("User deletion")

            #use different user for workload reassign with same tenant.
            rc = self.workload_reassign(CONF.identity.tenant_id, workload_id, CONF.identity.user_id_1)
            if rc == 0:
                LOG.debug("Workload reassign with different user is successful")
                reporting.add_test_step(
                    "Workload reassign with different user", tvaultconf.PASS)
            else:
                LOG.error("Workload reassign with different user is failed")
                raise Exception("Workload reassign with different user")


        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()




