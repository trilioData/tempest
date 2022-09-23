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
            user_details = self.createUser()
            if user_details == False:
                LOG.error("Failed to create user...")
                raise Exception("Failed to create user...")

            self.temp_user_id = user_details['id']
            self.temp_user_name = user_details['name']

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
            vm_id = self.create_vm()
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
                LOG.debug(f"User {self.temp_user_name} deleted successfully")
                reporting.add_test_step(
                    "User deletion", tvaultconf.PASS)
            else:
                LOG.error(f"User {self.temp_user_name} is not deleted successfully")
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
            user_details = self.createUser()
            if user_details == False:
                LOG.error("Failed to create user...")
                raise Exception("Failed to create user...")

            self.temp_user_id = user_details['id']
            self.temp_user_name = user_details['name']

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
            vm_id = self.create_vm()
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
                LOG.debug(f"User {self.temp_user_name} deleted successfully")
                reporting.add_test_step(
                    "User deletion", tvaultconf.PASS)
            else:
                LOG.error(f"User {self.temp_user_name} is not deleted successfully")
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



    '''
    OS-2063 - workload reassign with same user and same project after deletion of project.
    http://192.168.15.51/testlink/linkto.php?tprojectPrefix=OS&item=testcase&id=OS-2063
    '''
    @decorators.attr(type='workloadmgr_api')
    def test_06_workload_reassign(self):
        try:

            reporting.add_test_script(str(__name__) + "_same_user_same_tenant_after_deletion_of_project1")

            #create a temp user...
            user_details = self.createUser()
            if user_details == False:
                LOG.error("Failed to create user...")
                raise Exception("Failed to create user...")

            self.temp_user_id = user_details['id']
            self.temp_user_name = user_details['name']

            #assign trustee role
            role_id = self.get_role_id(tvaultconf.trustee_role)
            if len(role_id) != 1:
                raise Exception("Role ID not returned")

            #create temp project
            project_details = self.create_project()
            LOG.debug("Project created details - {}".format(project_details["name"]))
            self.temp_tenant_id = project_details["id"]
            self.temp_tenant_name = project_details["name"]

            #assign role to user and current project.
            if self.assign_role_to_user_project(self.temp_tenant_id,
                    self.temp_user_id, role_id[0], False):
                LOG.debug("Role assigned to user and project")
                reporting.add_test_step("Role assignment to user and project", tvaultconf.PASS)
            else:
                raise Exception("Role assignment to user and project failed")


            ### Create vm and workload ###
            self.created = False
            vm_id = self.create_vm()
            LOG.debug("\nVm id : {}\n".format(str(vm_id)))


            ### create workload ###
            workload_id = self.workload_create(
                [vm_id], tvaultconf.parallel)
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


            #use temp user and temp project for workload reassign.
            rc = self.workload_reassign(self.temp_tenant_id, workload_id, self.temp_user_id)
            if rc == 0:
                LOG.debug("Workload reassign to temp project with temp user is passed")
                reporting.add_test_step(
                    "Workload reassign to temp project with temp user", tvaultconf.PASS)
            else:
                LOG.error("Workload reassign to temp project with temp user is failed")
                raise Exception("Workload reassign to temp project with temp user")

            #delete the current created project.
            resp = self.delete_project(self.temp_tenant_id)
            if resp:
                LOG.debug(f"Project {self.temp_tenant_id} deleted successfully")
                reporting.add_test_step(
                    "Project deletion", tvaultconf.PASS)
            else:
                LOG.error(f"Project {self.temp_tenant_name} is not deleted successfully")
                raise Exception("Project deletion")

            #use same deleted temp project for workload reassign.
            rc = self.workload_reassign(self.temp_tenant_id, workload_id, self.temp_user_id)
            if rc == 0:
                LOG.debug("Workload reassign with same temp project and temp user is successful. Test case failed.")
                raise Exception("Workload reassign with temp project and temp user")
            else:
                LOG.error("Workload reassign on deleted temp project failed. Test case Passed")
                reporting.add_test_step(
                    "Workload reassign on deleted temp project failed.", tvaultconf.PASS)


        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()



    '''
    OS-2064 - workload reassign with same user and different project after deletion of project1.
    http://192.168.15.51/testlink/linkto.php?tprojectPrefix=OS&item=testcase&id=OS-2064
    '''
    @decorators.attr(type='workloadmgr_api')
    def test_07_workload_reassign(self):
        try:

            reporting.add_test_script(str(__name__) + "_same_user_different_tenant_after_deletion_of_temp_project1")

            #create a temp user...
            user_details = self.createUser()
            if user_details == False:
                LOG.error("Failed to create user...")
                raise Exception("Failed to create user...")

            self.temp_user_id = user_details['id']
            self.temp_user_name = user_details['name']
    
            #assign trustee role
            role_id = self.get_role_id(tvaultconf.trustee_role)
            if len(role_id) != 1:
                raise Exception("Role ID not returned")

            #create temp project 1
            project_details = self.create_project()
            LOG.debug("Project created details - {}".format(project_details["name"]))
            self.temp_tenant_id = project_details["id"]
            self.temp_tenant_name = project_details["name"]

            #create temp project 2
            project_details1 = self.create_project()
            LOG.debug("Project created details - {}".format(project_details1["name"]))
            self.temp_tenant_id_1 = project_details1["id"]
            self.temp_tenant_name_1 = project_details1["name"]


            #assign role to user and current project 1.
            if self.assign_role_to_user_project(self.temp_tenant_id,
                    self.temp_user_id, role_id[0], False):
                LOG.debug("Role assigned to user and project 1")
                reporting.add_test_step("Role assignment to user and project 1", tvaultconf.PASS)
            else:
                raise Exception("Role assignment to user and project 1 failed")

            #assign role to user and current project 2.
            if self.assign_role_to_user_project(self.temp_tenant_id_1,
                    self.temp_user_id, role_id[0], False):
                LOG.debug("Role assigned to user and project 2")
                reporting.add_test_step("Role assignment to user and project 2", tvaultconf.PASS)
            else:
                raise Exception("Role assignment to user and project 2 failed")

            ### Create vm and workload ###
            self.created = False
            vm_id = self.create_vm()
            LOG.debug("\nVm id : {}\n".format(str(vm_id)))


            ### create workload ###
            workload_id = self.workload_create(
                [vm_id], tvaultconf.parallel)
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


            #use temp user and temp project for workload reassign.
            rc = self.workload_reassign(self.temp_tenant_id, workload_id, self.temp_user_id)
            if rc == 0:
                LOG.debug("Workload reassign with temp project 1 and temp user is passed")
                reporting.add_test_step(
                    "Workload reassign with temp project 1 and temp user", tvaultconf.PASS)
            else:
                LOG.error("Workload reassign with temp project 1 and temp user is failed")
                raise Exception("Workload reassign with temp project 1 and temp user")

            #delete the current created project.
            resp = self.delete_project(self.temp_tenant_id)
            if resp:
                LOG.debug(f"Project 1 {self.temp_tenant_name} deleted successfully")
                reporting.add_test_step(
                    "Project 1 deletion", tvaultconf.PASS)
            else:
                LOG.error(f"Project 1 {self.temp_tenant_name} is not deleted successfully")
                raise Exception("Project 1 deletion")

            #use  temp project 2 for workload reassign.
            rc = self.workload_reassign(self.temp_tenant_id_1, workload_id, self.temp_user_id)
            if rc == 0:
                LOG.debug("Workload reassign with temp project 2 and temp user is passed.")
                reporting.add_test_step(
                    "Workload reassign with temp project 2 and temp user", tvaultconf.PASS)
            else:
                LOG.error("Workload reassign with temp project 2 and temp user is failed.")
                raise Exception("Workload reassign with temp project 2 and temp user")


        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()



    '''
    OS-2065 - workload reassign on same project and user(with trustee role), after deleting both
    http://192.168.15.51/testlink/linkto.php?tprojectPrefix=OS&item=testcase&id=OS-2065
    '''
    @decorators.attr(type='workloadmgr_api')
    def test_08_workload_reassign(self):
        try:

            reporting.add_test_script(str(__name__) + "_same_user_same_tenant_after_deletion_of_both")

            #create a temp user...
            user_details = self.createUser()
            if user_details == False:
                LOG.error("Failed to create user...")
                raise Exception("Failed to create user...")

            self.temp_user_id = user_details['id']
            self.temp_user_name = user_details['name']

            #assign trustee role
            role_id = self.get_role_id(tvaultconf.trustee_role)
            if len(role_id) != 1:
                raise Exception("Role ID not returned")

            #create temp project
            project_details = self.create_project()
            LOG.debug("Project created details - {}".format(project_details["name"]))
            self.temp_tenant_id = project_details["id"]
            self.temp_tenant_name = project_details["name"]

            #assign role to user and current project.
            if self.assign_role_to_user_project(self.temp_tenant_id,
                    self.temp_user_id, role_id[0], False):
                LOG.debug("Role assigned to user and project")
                reporting.add_test_step("Role assignment to user and project", tvaultconf.PASS)
            else:
                raise Exception("Role assignment to user and project failed")


            ### Create vm and workload ###
            self.created = False
            vm_id = self.create_vm()
            LOG.debug("\nVm id : {}\n".format(str(vm_id)))


            ### create workload ###
            workload_id = self.workload_create(
                [vm_id], tvaultconf.parallel)
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


            #use temp user and temp project for workload reassign.
            rc = self.workload_reassign(self.temp_tenant_id, workload_id, self.temp_user_id)
            if rc == 0:
                LOG.debug("Workload reassign to temp project with temp user is passed")
                reporting.add_test_step(
                    "Workload reassign to temp project with temp user", tvaultconf.PASS)
            else:
                LOG.error("Workload reassign to temp project with temp user is failed")
                raise Exception("Workload reassign to temp project with temp user")


            #delete the current created user.
            resp = self.deleteUser(self.temp_user_id)
            if resp:
                LOG.debug(f"User {self.temp_user_name} deleted successfully")
                reporting.add_test_step(
                    "User deletion", tvaultconf.PASS)
            else:
                LOG.error(f"User {self.temp_user_name} is not deleted successfully")
                raise Exception("User deletion")


            #delete the current created project.
            resp = self.delete_project(self.temp_tenant_id)
            if resp:
                LOG.debug(f"Project {self.temp_tenant_name} deleted successfully")
                reporting.add_test_step(
                    "Project deletion", tvaultconf.PASS)
            else:
                LOG.error(f"Project {self.temp_tenant_name} is not deleted successfully")
                raise Exception("Project deletion")


            #use same deleted temp project and temp user for workload reassign.
            rc = self.workload_reassign(self.temp_tenant_id, workload_id, self.temp_user_id)
            if rc == 0:
                LOG.debug("Workload reassign on deleted temp user and temp project is successful. Test case failed.")
                raise Exception("Workload reassign on deleted temp user and temp project passed.")
            else:
                LOG.error("Workload reassign on deleted temp user and temp project failed. Test case Passed")
                reporting.add_test_step(
                    "Workload reassign on deleted temp user and temp project failed.", tvaultconf.PASS)


        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()



    '''
    OS-2066 - workload reassign on different project and user(with trustee role), after deleting both user1 and project1
    http://192.168.15.51/testlink/linkto.php?tprojectPrefix=OS&item=testcase&id=OS-2066
    '''
    @decorators.attr(type='workloadmgr_api')
    def test_09_workload_reassign(self):
        try:

            reporting.add_test_script(str(__name__) + "_different_user_different_tenant_after_deletion_of_user1_tenant1")

            #create a temp user1...
            user_details1 = self.createUser()
            user_details2 = self.createUser()

            if user_details1 == False or user_details2 == False:
                LOG.error("Failed to create user...")
                raise Exception("Failed to create user...")


            self.temp_user_id_1 = user_details1['id']
            self.temp_user_name_1 = user_details1['name']

            self.temp_user_id_2 = user_details2['id']
            self.temp_user_name_2 = user_details2['name']

            #create temp project1...
            project_details_1 = self.create_project()
            LOG.debug("Project created details - {}".format(project_details_1["name"]))
            self.temp_tenant_id_1 = project_details_1["id"]
            self.temp_tenant_name_1 = project_details_1["name"]

            #create temp project2...
            project_details_2 = self.create_project()
            LOG.debug("Project created details - {}".format(project_details_2["name"]))
            self.temp_tenant_id_2 = project_details_2["id"]
            self.temp_tenant_name_2 = project_details_2["name"]

            #assign trustee role
            role_id = self.get_role_id(tvaultconf.trustee_role)
            if len(role_id) != 1:
                raise Exception("Role ID not returned")

            #assign role to user1 and current project1.
            if self.assign_role_to_user_project(self.temp_tenant_id_1,
                    self.temp_user_id_1, role_id[0], False):
                LOG.debug("Role assigned to user1 and project1")
                reporting.add_test_step("Role assignment to user1 and project1", tvaultconf.PASS)
            else:
                raise Exception("Role assignment to user1 and project1 failed")

            #assign role to user2 and current project2.
            if self.assign_role_to_user_project(self.temp_tenant_id_2,
                    self.temp_user_id_2, role_id[0], False):
                LOG.debug("Role assigned to user2 and project2")
                reporting.add_test_step("Role assignment to user2 and project2", tvaultconf.PASS)
            else:
                raise Exception("Role assignment to user2 and project2 failed")

            ### Create vm and workload ###
            self.created = False
            vm_id = self.create_vm()
            LOG.debug("\nVm id : {}\n".format(str(vm_id)))


            ### create workload ###
            workload_id = self.workload_create(
                [vm_id], tvaultconf.parallel)
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


            #use temp user and temp project for workload reassign.
            rc = self.workload_reassign(self.temp_tenant_id_1, workload_id, self.temp_user_id_1)
            if rc == 0:
                LOG.debug(f"Workload reassign to temp user1 {self.temp_user_name_1} with temp tenant1 {self.temp_tenant_name_1} is passed")
                reporting.add_test_step(
                    "Workload reassign to temp user1 {} with temp project1 {}".format(self.temp_user_name_1, self.temp_tenant_name_1), tvaultconf.PASS)
            else:
                LOG.error(f"Workload reassign to temp user1 {self.temp_user_name_1} with temp tenant1 {self.temp_tenant_name_1} is failed")
                raise Exception("Workload reassign to temp user1 {} with temp tenant1 {}".format(self.temp_user_name_1, self.temp_tenant_name_1))


            #delete the current created user.
            resp = self.deleteUser(self.temp_user_id_1)
            if resp:
                LOG.debug(f"temp User1 {self.temp_user_name_1} deleted successfully")
                reporting.add_test_step(
                    "temp User1 {} deletion".format(self.temp_user_name_1), tvaultconf.PASS)

            else:
                LOG.error(f"temp User1 {self.temp_user_name_1} is not deleted successfully")
                raise Exception("temp User1 {} deletion".format(self.temp_user_name_1))


            #delete the current created project.
            resp = self.delete_project(self.temp_tenant_id_1)
            if resp:
                LOG.debug(f"temp Project1 {self.temp_tenant_name_1} deleted successfully")
                reporting.add_test_step(
                    "temp Project1 {} deletion".format(self.temp_tenant_name_1), tvaultconf.PASS)
            else:
                LOG.error(f"temp Project1 {self.temp_tenant_name_1} is not deleted successfully")
                raise Exception("temp Project1 {} deletion".format(self.temp_tenant_name_1))


            #use same deleted temp project and temp user for workload reassign.
            rc = self.workload_reassign(self.temp_tenant_id_2, workload_id, self.temp_user_id_2)
            if rc == 0:
                LOG.debug(f"Workload reassign with temp user2 {self.temp_user_name_2} and temp project2 {self.temp_tenant_name_2} is successful.")
                reporting.add_test_step(
                    "Workload reassign with temp user2 {} and temp project2 {} passed".format(self.temp_user_name_2, self.temp_tenant_name_2), tvaultconf.PASS)
            else:
                LOG.error(f"Workload reassign with temp user2 {self.temp_user_name_2} and temp project2 {self.temp_tenant_name_2} failed.")
                raise Exception("Workload reassign with temp user2 {} and temp project2 {} failed.".format(self.temp_user_name_2, self.temp_tenant_name_2))

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()



