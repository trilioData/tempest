import os
import sys
import json
from oslo_log import log as logging
from tempest import command_argument_string
from tempest import config
from tempest import reporting
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

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    @decorators.attr(type='workloadmgr_cli')
    def test_01_list_quota_type(self):
        reporting.add_test_script(str(__name__) + "_list_quota_type_cli")
        try:
            rc = cli_parser.cli_returncode(
                command_argument_string.quota_type_list_count)
            if rc != 0:
                raise Exception("Execute project-quota-type-list command")
            else:
                reporting.add_test_step(
                    "Execute project-quota-type-list command", tvaultconf.PASS)

            wc = query_data.get_available_project_quota_types()
            out = cli_parser.cli_output(
                command_argument_string.quota_type_list_count)
            if (int(wc) == int(out)):
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.PASS)
            else:
                raise Exception("Verification with DB")
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_02_list_quota_type(self):
        reporting.add_test_script(str(__name__) + "_list_quota_type_api")
        try:
            quota_list = self.get_quota_type()
            if len(quota_list) > 0:
                reporting.add_test_step("List Quota types", tvaultconf.PASS)
            else:
                raise Exception("List Quota types")
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_03_workload_quota(self):
        reporting.add_test_script(str(__name__) + "_workload_api")
        try:
            # Create workload quota
            self.project_id = CONF.identity.tenant_id
            self.quota_type_name = "Workloads"
            self.quota_type_id = self.get_quota_type_id(self.quota_type_name)
            self.quota_id = self.create_project_quota(self.project_id,
                    self.quota_type_id, tvaultconf.workload_allowed_value,
                    tvaultconf.workload_watermark_value, quota_cleanup=False)
            if self.quota_id:
                reporting.add_test_step("Create workload quota for project", tvaultconf.PASS)
            else:
                raise Exception("Create workload quota for project")

            self.instances = []
            for i in range(tvaultconf.workload_allowed_value+2):
                self.vm_id = self.create_vm()
                self.instances.append(self.vm_id)
            self.workload_id1 = self.workload_create([self.instances[0]])
            if self.workload_id1:
                reporting.add_test_step("Create workload-1 in project", tvaultconf.PASS)
            else:
                raise Exception("Create workload-1 in project")
            try:
                self.workload_id2 = self.workload_create([self.instances[1]])
                if self.workload_id2:
                    raise Exception("Able to create workload-2 in project")
            except Exception as e:
                LOG.error("Exception: " + str(e))
                reporting.add_test_step(
                    "Unable to create workload-2 in project", tvaultconf.PASS)

            #Update workload quota
            update_resp = self.update_project_quota(self.project_id,
                                        self.quota_id,
                                        tvaultconf.workload_allowed_value+1,
                                        tvaultconf.workload_watermark_value+1)
            if update_resp:
                reporting.add_test_step("Update project quota",
                                        tvaultconf.PASS)
            else:
                raise Exception("unable to update project quota")
            try:
                self.workload_id2 = self.workload_create([self.instances[1]])
                if self.workload_id2:
                    reporting.add_test_step("Create workload-2 in project",
                                            tvaultconf.PASS)
            except Exception as e:
                LOG.error("Exception: " + str(e))
                raise Exception("Unable to create workload-2 in project")

            #List quotas
            self.quota_list = self.get_quota_list(self.project_id)
            if len(self.quota_list) > 0:
                reporting.add_test_step("List project quotas", tvaultconf.PASS)
            else:
                reporting.add_test_step("List project quotas", tvaultconf.FAIL)
                LOG.error("Quota list %s " % self.quota_list)

            #Show project quota
            quota_act = self.get_quota_details(self.quota_id)
            quota_exp = {"id": self.quota_id, "project_id": self.project_id,
                         "quota_type_id": self.quota_type_id,
                         "allowed_value": tvaultconf.workload_allowed_value+1,
                         "high_watermark": tvaultconf.workload_watermark_value+1,
                         "version": tvaultconf.tvault_version,
                         "quota_type_name": self.quota_type_name}
            if quota_act == quota_exp:
                reporting.add_test_step("Verify project allowed quota show",
                                        tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify project allowed quota show",
                                        tvaultconf.FAIL)
                LOG.error("Expected quota show %s, Actual quota show %s" %
                          (quota_exp, quota_act))

            #Delete project quota
            self.quota_del = self.delete_project_quota(self.quota_id)
            if self.quota_del:
                reporting.add_test_step("Delete project quota",
                                        tvaultconf.PASS)
            else:
                reporting.add_test_step("Delete project quota",
                                        tvaultconf.FAIL)

            #Verify quota delete
            self.quota_list = self.get_quota_list(self.project_id)
            if len(self.quota_list) == 0:
                reporting.add_test_step("Verify project quota delete",
                                        tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify project quota delete",
                                        tvaultconf.FAIL)
                LOG.error("Quota list %s " % self.quota_list)

            #Create workload after quota delete
            try:
                self.workload_id3 = self.workload_create([self.instances[2]])
                if self.workload_id3:
                    reporting.add_test_step("Create workload-3 in project",
                                            tvaultconf.PASS)
            except Exception as e:
                raise Exception(e)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_04_workload_quota(self):
        reporting.add_test_script(str(__name__) + "_workload_cli")
        try:
            # Create workload quota
            self.project_id = CONF.identity.tenant_id
            self.quota_type_name = "Workloads"

            rc = cli_parser.cli_returncode(
                    command_argument_string.quota_type_list)
            if rc:
                raise Exception("Execute project-quota-type-list command")
            else:
                reporting.add_test_step(
                    "Execute project-quota-type-list command", tvaultconf.PASS)
            self.quota_type_id = self.get_quota_type_id_cli(
                                        self.quota_type_name)

            #Create project allowed quota
            cmd_quota_create = command_argument_string.quota_create + \
                "--quota-type-id " + str(self.quota_type_id) + \
                " --allowed-value " + str(tvaultconf.workload_allowed_value) +\
                " --high-watermark " + str(tvaultconf.workload_watermark_value)\
                + " --project-id " + str(self.project_id)
            rc = cli_parser.cli_returncode(cmd_quota_create)
            if rc:
                raise Exception(
                    "Execute project-allowed-quota-create for workloads")
            else:
                reporting.add_test_step(
                    "Execute project-allowed-quota-create for workloads",
                    tvaultconf.PASS)

            self.quota_id = query_data.get_quota_id(self.quota_type_id,
                                                    self.project_id)
            if self.quota_id:
                reporting.add_test_step("Create workload quota for project",
                                        tvaultconf.PASS)
            else:
                raise Exception("Create workload quota for project")

            self.instances = []
            for i in range(tvaultconf.workload_allowed_value+2):
                self.vm_id = self.create_vm()
                self.instances.append(self.vm_id)
            self.workload_id1 = self.workload_create([self.instances[0]])
            if self.workload_id1:
                reporting.add_test_step("Create workload-1 in project",
                                        tvaultconf.PASS)
            else:
                raise Exception("Create workload-1 in project")
            try:
                self.workload_id2 = self.workload_create([self.instances[1]])
                if self.workload_id2:
                    raise Exception("Able to create workload-2 in project")
            except Exception as e:
                LOG.error("Exception: " + str(e))
                reporting.add_test_step("Unable to create workload-2 in project", tvaultconf.PASS)

            #Update workload quota
            cmd_quota_update = command_argument_string.quota_update + \
                " --allowed-value " + \
                str(int(tvaultconf.workload_allowed_value+1)) + \
                " --high-watermark " + \
                str(int(tvaultconf.workload_watermark_value+1)) + \
                " --project-id " + str(self.project_id) + " " + \
                               str(self.quota_id)
            rc = cli_parser.cli_returncode(cmd_quota_update)
            if rc:
                raise Exception("Execute project-allowed-quota-update")
            else:
                reporting.add_test_step("Execute project-allowed-quota-update",
                                        tvaultconf.PASS)

            #List quotas
            cmd_quota_list = command_argument_string.quota_list + \
                             str(self.project_id)
            rc = cli_parser.cli_returncode(cmd_quota_list)
            if rc:
                reporting.add_test_step("Execute project-allowed-quota-list",
                                        tvaultconf.FAIL)
            else:
                reporting.add_test_step("Execute project-allowed-quota-list",
                                        tvaultconf.PASS)

            #Verify quota list with DB
            cmd_quota_list = command_argument_string.quota_list + \
                             str(self.project_id)

            #Show project allowed quota
            cmd_quota_show = command_argument_string.quota_show + \
                             str(self.quota_id)
            out = cli_parser.cli_output(cmd_quota_show)
            if out:
                reporting.add_test_step("Execute project-allowed-quota-show",
                                        tvaultconf.PASS)
            else:
                reporting.add_test_step("Execute project-allowed-quota-show",
                                        tvaultconf.FAIL)

            quota_act = out.split('\n')
            for i in range(len(quota_act)):
                if i < 2:
                    quota_act[i] = int(quota_act[i])
            quota_act = list(filter(None, quota_act))
            quota_db = list(query_data.get_quota_details(self.quota_id))
            if quota_act == quota_db:
                reporting.add_test_step("Verify project allowed quota show",
                                        tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify project allowed quota show",
                                        tvaultconf.FAIL)
                LOG.error("Expected quota show %s, Actual quota show %s" %
                          (quota_db, quota_act))

            try:
                self.workload_id2 = self.workload_create([self.instances[1]])
                if self.workload_id2:
                    reporting.add_test_step("Create workload-2 in project",
                                            tvaultconf.PASS)
            except Exception as e:
                LOG.error("Exception: " + str(e))
                raise Exception("Unable to create workload-2 in project")


            #Delete project quota
            cmd_quota_delete = command_argument_string.quota_delete + \
                               str(self.quota_id)
            rc = cli_parser.cli_returncode(cmd_quota_delete)
            if rc:
                reporting.add_test_step("Execute project-allowed-quota-delete",
                                        tvaultconf.FAIL)
            else:
                reporting.add_test_step("Execute project-allowed-quota-delete",
                                        tvaultconf.PASS)

            #Verify quota delete
            wc = query_data.get_available_quotas_count(self.project_id)
            if wc == 0:
                reporting.add_test_step("Verify project quota delete",
                                        tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify project quota delete",
                                        tvaultconf.FAIL)

            #Create workload after quota delete
            try:
                self.workload_id3 = self.workload_create([self.instances[2]])
                if self.workload_id3:
                    reporting.add_test_step("Create workload-3 in project",
                                            tvaultconf.PASS)
            except Exception as e:
                raise Exception(e)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_05_vm_quota(self):
        reporting.add_test_script(str(__name__) + "_vms_api")
        try:
            # Create workload quota
            self.project_id = CONF.identity.tenant_id
            self.quota_type_name = "VMs"
            self.quota_type_id = self.get_quota_type_id(self.quota_type_name)
            self.quota_id = self.create_project_quota(self.project_id,
                                                  self.quota_type_id,
                                                  tvaultconf.vm_allowed_value,
                                                  tvaultconf.vm_watermark_value,
                                                  quota_cleanup=False)
            if self.quota_id:
                reporting.add_test_step("Create VM quota for project",
                                    tvaultconf.PASS)
            else:
                raise Exception("Create VM quota for project")

            self.instances = []
            for i in range(tvaultconf.vm_allowed_value + 3):
                self.vm_id = self.create_vm()
                self.instances.append(self.vm_id)
            self.workload_id1 = self.workload_create([self.instances[0]])
            if self.workload_id1:
                reporting.add_test_step("Create workload-1 with 1 VM",
                                    tvaultconf.PASS)
            else:
                raise Exception("Create workload-1 with 1 VM")
            try:
                self.workload_modify(self.workload_id1,
                                     [self.instances[0], self.instances[1]])
                raise Exception("Able to update workload-1 and "
                            "add 2nd VM to workload")
            except Exception as e:
                LOG.error("Exception: " + str(e))
                reporting.add_test_step(
                    "Unable to update workload-1 and add 2nd VM to workload",
                    tvaultconf.PASS)
            try:
                self.workload_id2 = self.workload_create([self.instances[1]])
                if self.workload_id2:
                    raise Exception("Able to create workload-2 with 1 VM")
            except Exception as e:
                LOG.error("Exception: " + str(e))
                reporting.add_test_step(
                    "Unable to create workload-2 with 1 VM", tvaultconf.PASS)

            # Update vm quota
            update_resp = self.update_project_quota(self.project_id,
                                                self.quota_id,
                                                tvaultconf.vm_allowed_value + 1,
                                                tvaultconf.vm_watermark_value + 1)
            if update_resp:
                reporting.add_test_step("Update project quota to 2",
                                        tvaultconf.PASS)
            else:
                raise Exception("unable to update project quota to 2")
            try:
                self.workload_id2 = self.workload_create([self.instances[1]])
                if self.workload_id2:
                    reporting.add_test_step("Create workload-2 in project",
                                            tvaultconf.PASS)
            except Exception as e:
                LOG.error("Exception: " + str(e))
                raise Exception("Unable to create workload-2 in project")
            try:
                self.workload_modify(self.workload_id1,
                                     [self.instances[0], self.instances[2]])
                raise Exception("Able to update workload-1 and "
                                "add 2nd VM to workload")
            except Exception as e:
                LOG.error("Exception: " + str(e))
                reporting.add_test_step(
                    "Unable to update workload-1 and add 2nd VM to workload",
                    tvaultconf.PASS)

            update_resp = self.update_project_quota(self.project_id,
                                                    self.quota_id,
                                                    0, 0)
            if update_resp:
                reporting.add_test_step("Update project quota to 0",
                                        tvaultconf.PASS)
            else:
                raise Exception("unable to update project quota to 0")
            try:
                self.workload_modify(self.workload_id1,
                                     [self.instances[0], self.instances[2],
                                      self.instances[3]])
                raise Exception("Able to update workload-1 and "
                                "add 2nd VM to workload")
            except Exception as e:
                LOG.error("Exception: " + str(e))
                reporting.add_test_step(
                    "Unable to update workload-1 and add 2nd VM to workload",
                    tvaultconf.PASS)
            try:
                self.workload_id3 = self.workload_create([self.instances[2]])
                raise Exception("Able to create new workload")
            except Exception as e:
                LOG.error("Exception: " + str(e))
                reporting.add_test_step(
                    "Unable to create new workload-3", tvaultconf.PASS)
            try:
                self.workload_modify(self.workload_id2,
                                     [self.instances[0], self.instances[2]])
                raise Exception("Able to update workload-2 and " +
                            "add new VM to workload")
            except Exception as e:
                LOG.error("Exception: " + str(e))
                reporting.add_test_step(
                    "Unable to update workload-1 and add 2nd VM to workload",
                    tvaultconf.PASS)

            # Show project quota
            quota_act = self.get_quota_details(self.quota_id)
            quota_exp = {"id": self.quota_id, "project_id": self.project_id,
                         "quota_type_id": self.quota_type_id,
                         "allowed_value": 0,
                         "high_watermark": 0,
                         "version": tvaultconf.tvault_version,
                         "quota_type_name": self.quota_type_name}
            if quota_act == quota_exp:
                reporting.add_test_step("Verify project allowed quota show",
                                        tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify project allowed quota show",
                                        tvaultconf.FAIL)
                LOG.error("Expected quota show %s, Actual quota show %s" %
                          (quota_exp, quota_act))

            # Delete project quota
            self.quota_del = self.delete_project_quota(self.quota_id)
            if self.quota_del:
                reporting.add_test_step("Delete project quota",
                                        tvaultconf.PASS)
            else:
                reporting.add_test_step("Delete project quota",
                                        tvaultconf.FAIL)

            # Verify quota delete
            self.quota_list = self.get_quota_list(self.project_id)
            if len(self.quota_list) == 0:
                reporting.add_test_step("Verify project quota delete",
                                        tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify project quota delete",
                                        tvaultconf.FAIL)
                LOG.error("Quota list %s " % self.quota_list)

            # Create workload after quota delete
            try:
                self.workload_id3 = self.workload_create([self.instances[3]])
                if self.workload_id3:
                    reporting.add_test_step("Create workload-3 in project",
                                            tvaultconf.PASS)
            except Exception as e:
                raise Exception(e)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()
