import os
import sys
import time
import random

from oslo_log import log as logging

from tempest import config
from tempest import command_argument_string
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
    credentials = ["primary"]

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    def _create_workload(self, vms):
        LOG.debug("\nvms : {}\n".format(vms))
        workload_id = self.workload_create(
            instances=vms,
            workload_type=tvaultconf.parallel,
            workload_name="for_security_group",
            workload_cleanup=True,
        )
        LOG.debug("Workload ID: " + str(workload_id))
        if workload_id is not None:
            self.wait_for_workload_tobe_available(workload_id)
            if self.getWorkloadStatus(workload_id) == "available":
                reporting.add_test_step(
                    "Create workload", tvaultconf.PASS)
        else:
            reporting.add_test_step(
                "Create workload", tvaultconf.FAIL)
            raise Exception("Workload creation failed")
        return workload_id

    def _take_full_snapshot(self, workload_id):
        snapshot_id = self.workload_snapshot(workload_id, True, snapshot_cleanup=True)
        time.sleep(5)
        self.wait_for_workload_tobe_available(workload_id)
        if self.getSnapshotStatus(workload_id, snapshot_id) == "available":
            reporting.add_test_step(
                "Create full snapshot", tvaultconf.PASS)
            LOG.debug("Full snapshot available!!")
        else:
            reporting.add_test_step(
                "Create full snapshot", tvaultconf.FAIL)
            raise Exception("Snapshot creation failed")
        LOG.debug("\nFull snapshot ids : {}\n".format(snapshot_id))
        return snapshot_id

    def _restore_through_wlm_cli(self, snapshot_id):
        restore_command = command_argument_string.restore_security_groups +\
                " " + snapshot_id
        rc = cli_parser.cli_returncode(restore_command)
        if rc != 0:
            reporting.add_test_step(
                "Execute restore security groups command", tvaultconf.FAIL)
            raise Exception("Command did not execute correctly")
        else:
            reporting.add_test_step(
                "Execute restore security groups command", tvaultconf.PASS)
            LOG.debug("Command executed correctly")

        time.sleep(10)
        # DB verification of the command execution
        wc = query_data.get_snapshot_restore_status(
            tvaultconf.security_group_restore_name, snapshot_id
        )
        LOG.debug("Security group restore status: " + str(wc))
        while str(wc) != "available" and str(wc) != "error":
            time.sleep(5)
            wc = query_data.get_snapshot_restore_status(
                tvaultconf.security_group_restore_name, snapshot_id)
            LOG.debug("Snapshot restore status: " + str(wc))
        if str(wc) == "available":
            reporting.add_test_step(
                "Security group restore command verification",
                tvaultconf.PASS)
        else:
            reporting.add_test_step(
                "security group restore command verification",
                tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

    # Generate security groups and rules data
    def _generate_data_for_secgrp(self, security_group_count, rules_count):
        secgrp_list_with_rules = []
        ip_protocols = ["tcp", "udp"]
        for t in range(1, security_group_count + 1):
            rules_dict = []
            for i in range(0, rules_count):
                protocol = random.choice(ip_protocols)
                from_port = random.randrange(1500, 15000)
                to_port = random.randrange(16000, 30000)
                values = {
                    "protocol": protocol,
                    "port_range_min": from_port,
                    "port_range_max": to_port,
                }
                rules_dict.append(values)
            secgrp_list_with_rules.append(rules_dict)
        LOG.debug("sec group + rules: {}".format(secgrp_list_with_rules))
        return secgrp_list_with_rules

    """ Method to create Security groups with distinct rules """

    def _create_sec_groups_rule(self, security_group_names, data_sec_group_and_rules,
                                tenant_id=CONF.identity.tenant_id):
        LOG.debug("Create security group and rule")
        created_security_groups = []
        for each in range(1, len(data_sec_group_and_rules) + 1):
            sgid = self.create_security_group(
                name=security_group_names + format(each),
                description="security group with distinct rules",
                tenant_id=tenant_id,
                secgrp_cleanup=True,
            )
            created_security_groups.append(sgid)
            # Delete default security group rules
            self.delete_default_rules(sgid)
        for t in range(0, len(created_security_groups)):
            LOG.debug("Creating rule with other details")
            secgrp = created_security_groups[t]
            for each in data_sec_group_and_rules[t]:
                self.add_security_group_rule(
                    parent_grp_id=secgrp,
                    ip_proto=each["protocol"],
                    from_prt=each["port_range_min"],
                    to_prt=each["port_range_max"])
        return created_security_groups

    def _security_group_verification_post_restore(self, restored_secgrps):
        for restored_secgrp in restored_secgrps:
            LOG.debug("Print names of restored security groups : {}".format(
                    restored_secgrp["name"]))
            if self.verifySecurityGroupsByname(restored_secgrp["name"]):
                reporting.add_test_step(
                    "Security group verification successful for restored vm {}".format(
                        restored_secgrp["name"]), tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Security group verification failed for restored vm {}".format(
                        restored_secgrp["name"]), tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

    def _security_group_and_rules_verification(self, security_group_names, 
            data_sec_group_and_rules, rules_count):
        restored_secgroup_ids = []
        for t in range(0, len(data_sec_group_and_rules)):
            restored_security_group = security_group_names + str(t + 1)
            sgid = self.get_restored_security_group_id_by_name(restored_security_group)
            if sgid:
                LOG.debug("security group is restored: {}".format(sgid))
            else:
                sgid = self.get_security_group_id_by_name(restored_security_group)
                LOG.debug("Original security group is present: {}".format(sgid))
            # restored security groups to be cleaned after the execution
            restored_secgroup_ids.append(sgid)
            rule_list = self.list_secgroup_rules_for_secgroupid(sgid)
            count = 0

            for each in data_sec_group_and_rules[t]:
                for rule in rule_list:
                    result = self.verifySecurityGroupRules(rule["id"], sgid, each)
                    if result == True:
                        count += 1
                LOG.debug("Here is the count: {} for restored rules per "\
                        + "security group {}".format(count, each))

            if count == rules_count * 2:
                reporting.add_test_step(
                    "Security group rules verification successful for "\
                            "restored secgroup {}".format(
                                restored_security_group), tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Security group rules verification failed for "\
                        "restored secgroup {}".format(restored_security_group),
                        tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
        return restored_secgroup_ids

    def _perform_selective_restore(self, vms, volumes, workload_id, snapshot_id):
        rest_details = {
            "rest_type": "selective",
            "network_id": CONF.network.internal_network_id,
            "subnet_id": self.get_subnet_id(CONF.network.internal_network_id),
            "instances": {vms[0]: volumes},
        }

        payload = self.create_restore_json(rest_details)
        # Trigger selective restore of full snapshot
        restore_id = self.snapshot_selective_restore(
            workload_id,
            snapshot_id,
            restore_name=tvaultconf.selective_restore_name,
            restore_cleanup=True,
            instance_details=payload["instance_details"],
            network_details=payload["network_details"]
        )

        if self.getRestoreStatus(workload_id, snapshot_id, restore_id) == "available":
            reporting.add_test_step(
                "Selective restore completed successfully", tvaultconf.PASS)
            LOG.debug("selective restore passed")
        else:
            reporting.add_test_step("Selective restore failed", tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
            LOG.error("selective restore failed")
        return restore_id

    def _perform_oneclick_restore(self, workload_id, snapshot_id):
        restore_id = self.snapshot_restore(
            workload_id, snapshot_id, restore_cleanup=True
        )
        self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
        if self.getRestoreStatus(workload_id, snapshot_id, restore_id) == \
                "available":
            reporting.add_test_step(
                "Oneclick restore completed successfully", tvaultconf.PASS
            )
            LOG.debug("Oneclick restore passed")
        else:
            LOG.error("Oneclick restore failed")
            reporting.add_test_step(
                "Oneclick restore failed", tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        return restore_id

    def _delete_vms_secgroups(self, vms, secgroup_ids):
        try:
            self.delete_vm_secgroups(vms, secgroup_ids)
            reporting.add_test_step(
                "Delete vms and security groups before proceeding with restore",
                tvaultconf.PASS,
            )
            LOG.debug(
                "Remaining security groups after deletion {} ".format(
                    self.list_security_groups()
                )
            )
        except Exception as e:
            LOG.error(f"Exception: {e}")
            raise Exception("Deletion of vms and security group/s failed")
        time.sleep(60)

    def _concat_lists(self, list1, list2, list3=None):
        for sec_grp2 in list2:
            if 'name' in sec_grp2.keys() and sec_grp2['name'] == "default":
                list2.remove(sec_grp2)
        list1 = list1 + list2
        if list3 != None:
            for sec_grp3 in list3:
                if 'name' in sec_grp3.keys() and sec_grp3['name'] == "default":
                    list3.remove(sec_grp3)
            list1 = list1 + list3
        return list1


    # Test case automation for #OS-1892 : Security_Group_Restore_using_CLI_for_single_group
    # Test case automation for #OS-1893 : Security_Group_Restore_using_CLI_for_multiple_groups
    @decorators.attr(type="workloadmgr_cli")
    def test_01_security_group(self):
        test_var = "tempest.api.workloadmgr.security_group.test_"
        tests = [[test_var + "wlm_cli_single_security_group", 1, 3],
                 [test_var + "wlm_cli_multiple_security_groups", 5, 3]]

        for test in tests:
            restored_secgroup_ids = []
            try:
                reporting.add_test_script(test[0])
                LOG.debug(
                    "Create Security group/s with distinct rules"
                )
                security_group_names = tvaultconf.security_group_name
                security_group_count = test[1]
                rules_count = test[2]

                try:
                    data_sec_group_and_rules = self._generate_data_for_secgrp(security_group_count, rules_count)
                    created_security_groups = self._create_sec_groups_rule(security_group_names,
                                                                           data_sec_group_and_rules)
                    reporting.add_test_step("creating security group/s with distinct rules", tvaultconf.PASS)
                except Exception as e:
                    LOG.error(f"Exception: {e}")
                    raise Exception("Security group and rules creation failed")

                # Create an image booted instance with Security group and attach an volume.
                LOG.debug(
                    "Create an image booted instance with Security group and attach an volume"
                )
                # Create volume
                self.volume_id = self.create_volume(volume_cleanup=True)
                LOG.debug("Volume ID: " + str(self.volume_id))

                # create vm
                self.vm_id = self.create_vm(security_group_id=created_security_groups[0], vm_cleanup=True)
                LOG.debug("Vm ID: " + str(self.vm_id))

                # Attach volume to the instance
                self.attach_volume(self.volume_id, self.vm_id, attach_cleanup=True)
                LOG.debug("Volume attached")

                # Assign additional security groups if provided
                LOG.debug("Security groups before adding to instance: {}".format(created_security_groups))
                for i in range(1, security_group_count):
                    result = self.add_security_group_to_instance(self.vm_id, created_security_groups[i])
                    if result == False:
                        raise Exception("Add security group to instance failed")
                LOG.debug("Assigned all security groups to instance")

                # Create a workload for the instance.
                LOG.debug("Create a workload for this instance.")
                workload_id = self._create_workload([self.vm_id])
                LOG.debug("\nWorkload created : {}\n".format(workload_id))

                # Take a Full snapshot
                LOG.debug("Take a full snapshot")
                snapshot_id = self._take_full_snapshot(workload_id)

                # Get the sec groups and rules list for verification post restore
                secgroups_before = self.list_security_groups()
                rules_before = self.list_security_group_rules()

                # Delete vms, volumes, security groups
                try:
                    LOG.debug("Delete VM + volume + security groups")
                    self.delete_vm_secgroups([self.vm_id], created_security_groups)
                    reporting.add_test_step(
                        "Delete vm and security group", tvaultconf.PASS
                    )
                except Exception as e:
                    LOG.error(f"Exception: {e}")
                    raise Exception("Deletion of vm and security group/s failed")
                time.sleep(60)

                # Perform security groups restore through wlm command
                self._restore_through_wlm_cli(snapshot_id)

                # Security group and rules verification post restore
                LOG.debug("Compare the security groups before and after restore")
                secgroups_after = self.list_security_groups()
                if len(secgroups_after) == len(secgroups_before):
                    reporting.add_test_step(
                        "Security group verification pre and post restore",
                        tvaultconf.PASS,
                    )
                else:
                    LOG.error("Security groups verification pre and post restore")
                    reporting.add_test_step(
                        "Security groups verification failed pre and post restore",
                        tvaultconf.FAIL,
                    )
                    reporting.set_test_script_status(tvaultconf.FAIL)

                LOG.debug("Compare the security group rules before and after restore")
                rules_after = self.list_security_group_rules()
                if len(rules_after) == len(rules_before):
                    reporting.add_test_step(
                        "Security group rules verification pre and post restore",
                        tvaultconf.PASS,
                    )
                else:
                    reporting.add_test_step(
                        "Security group rules verification pre and post restore",
                        tvaultconf.FAIL,
                    )
                    reporting.set_test_script_status(tvaultconf.FAIL)

                LOG.debug("Comparing restored security group & rules for {}".format(tvaultconf.security_group_name))
                restored_secgroup_ids = self._security_group_and_rules_verification(security_group_names,
                                                                                    data_sec_group_and_rules,
                                                                                    rules_count)

            except Exception as e:
                LOG.error("Exception: " + str(e))
                reporting.add_test_step(str(e), tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            finally:
                reporting.test_case_to_write()
                # Deleting restored security groups after verification
                if len(restored_secgroup_ids) != 0:
                    for secgrp in restored_secgroup_ids:
                        LOG.debug("Deleting security groups: {}".format(secgrp))
                        self.delete_security_group(secgrp)

    # Test case automation for #OS-2028 : Shared Security_Group_Restore
    # http://192.168.15.51/testlink/linkto.php?tprojectPrefix=OS&item=testcase&id=OS-2028
    @decorators.attr(type="workloadmgr_api")
    def test_02_shared_security_group(self):
        test_var = "tempest.api.workloadmgr.security_group.test_"
        tests = [
            [test_var + "shared_security_group_restore_delete_vm_secgrp_shared", 1, 3, "delete_vm_secgrp_shared"],
            [test_var + "shared_security_group_restore_delete_vm_secgrp", 1, 3, "delete_vm_secgrp"],
            [test_var + "shared_security_group_restore_delete_vm", 1, 3, "delete_vm"],
            [test_var + "shared_security_group_restore_no_delete", 1, 3, "no_delete"],
        ]

        tenant_id = CONF.identity.tenant_id
        tenant_id_1 = CONF.identity.tenant_id_1

        for test in tests:
            try:
                restore_tests = [[test[0] + "_selectiverestore_api", "selective"],
                                 [test[0] + "_oneclickrestore_api", "oneclick"]]
                reporting.add_test_script(restore_tests[0][0])
                security_group_count = test[1]
                rules_count = test[2]

                LOG.debug("Create shared Security group/s with distinct rules")
                security_group_names_projA = tvaultconf.security_group_name + str(random.randint(0, 10000))
                security_group_names_projB = tvaultconf.security_group_name + str(random.randint(0, 10000))
                try:
                    # create security group in project A (tenant_id_1)
                    LOG.debug(
                        "Setting project to project-A: {} and {}".format(CONF.identity.project_alt_name, tenant_id_1))
                    data_sec_group_and_rules_tenantA = self._generate_data_for_secgrp(
                        security_group_count, rules_count
                    )
                    security_groups_tenantA = self._create_sec_groups_rule(
                        security_group_names_projA,
                        data_sec_group_and_rules_tenantA,
                        tenant_id_1
                    )
                    print("project A sec group id: {}".format(security_groups_tenantA[0]))
                    reporting.add_test_step(
                        "creating shared security group/s {} with distinct rules in project-A ".format(
                            security_group_names_projA + str(1)),
                        tvaultconf.PASS,
                    )

                    # Create the RBAC policy entry using the openstack network rbac create and share the above created security_group with project-B
                    rbac_command = command_argument_string.rbac_create_secgroup + tenant_id + " --action access_as_shared --type security_group " + \
                                   security_groups_tenantA[0]
                    LOG.debug("rbac command: {}".format(rbac_command))
                    rc = cli_parser.cli_returncode(rbac_command)
                    if rc != 0:
                        reporting.add_test_step(
                            "Execute create rbac policy for security group",
                            tvaultconf.FAIL,
                        )
                        raise Exception("rbac command did not execute correctly")
                    else:
                        reporting.add_test_step(
                            "Execute create rbac policy for security group",
                            tvaultconf.PASS,
                        )
                    time.sleep(10)

                    # Create security group in project-B (tenant_id)
                    LOG.debug("Setting project to project-B: {} and {}".format(CONF.identity.project_name, tenant_id))
                    data_sec_group_and_rules_tenantB = self._generate_data_for_secgrp(
                        security_group_count, rules_count
                    )
                    security_groups_tenantB = self._create_sec_groups_rule(
                        security_group_names_projB,
                        data_sec_group_and_rules_tenantB,
                    )
                    print("project B sec group id: {}".format(security_groups_tenantB[0]))

                    # create security_group_rule for the sec_group created in above step, attach the remote-sec-group as the shared sec_group.
                    LOG.debug("Create security group rule with shared security group")
                    self.add_security_group_rule(
                        parent_grp_id=security_groups_tenantB[0],
                        remote_grp_id=security_groups_tenantA[0],
                        ip_proto="tcp",
                        from_prt=1567,
                        to_prt=3269,
                    )
                    reporting.add_test_step(
                        "creating security group/s {} with shared security group from project-A ".format(
                            security_group_names_projB + str(1)),
                        tvaultconf.PASS,
                    )
                except Exception as e:
                    LOG.error(f"Exception: {e}")
                    raise Exception("Shared security group and rules creation failed")

                # Create an image booted instance with Security group and attach an volume.
                LOG.debug(
                    "Create an image booted instance with Security group and attach an volume"
                )
                # Create volume
                self.volume_id = self.create_volume(volume_cleanup=True)
                LOG.debug("Volume ID: " + str(self.volume_id))

                # create vm
                self.vm_id = self.create_vm(
                    security_group_id=security_groups_tenantB[0], vm_cleanup=True
                )
                LOG.debug("Vm ID: " + str(self.vm_id))

                # Attach volume to the instance
                self.attach_volume(self.volume_id, self.vm_id, attach_cleanup=True)
                LOG.debug("Volume attached")

                # Create a workload for the instance.
                LOG.debug("Create a workload for this instance.")
                workload_id = self._create_workload([self.vm_id])
                LOG.debug("\nWorkload created : {}\n".format(workload_id))

                # Take a Full snapshot
                LOG.debug("Take a full snapshot")
                snapshot_id = self._take_full_snapshot(workload_id)

                # Get the sec groups and rules list for verification post restore
                secgroups_before1 = self.list_security_groups()
                secgroups_before2 = self.list_security_groups(tenant_id_1)
                rules_before = self.list_security_group_rules()

                secgroups_before = self._concat_lists(secgroups_before1,secgroups_before2)
                LOG.debug("Security groups before : {}".format(secgroups_before))
                LOG.debug("Security group rules before : {}".format(rules_before))

                # Delete security group assigned to instance as per the test steps
                delete_secgrp_ids = []
                if (test[3] == "delete_vm_secgrp"):
                    delete_secgrp_ids = [security_groups_tenantB[0]]

                # Delete security group assigned to instance and shared security group
                if (test[3] == "delete_vm_secgrp_shared"):
                    delete_secgrp_ids = [security_groups_tenantA[0], security_groups_tenantB[0]]

                # Delete vm, volumes, security groups as per the test step
                try:
                    if (test[3] != "no_delete"):
                        vol = []
                        for vm in [self.vm_id]:
                            LOG.debug("Get list of all volumes to be deleted from instance {}".format(vm))
                            vol.append(self.get_attached_volumes(vm))
                        self.delete_vms([self.vm_id])
                        LOG.debug("Delete volumes: {}".format(vol))
                        self.delete_volumes(vol)
                        reporting.add_test_step("Deleted vm {} before proceeding with restore".format(self.vm_id),
                                                tvaultconf.PASS, )
                        time.sleep(10)

                        if delete_secgrp_ids:
                            for secgrp in delete_secgrp_ids:
                                self.delete_security_group(secgrp)
                                LOG.debug(
                                    "Delete security group assigned to instance and shared security group: {}".format(
                                        secgrp))
                            reporting.add_test_step(
                                "Deleted security groups/shared security group {} before proceeding with restore".format(
                                    delete_secgrp_ids),
                                tvaultconf.PASS, )

                except Exception as e:
                    LOG.error(f"Exception: {e}")
                    raise Exception("Deletion of vms/security group/Shared security group failed")

                # Perform restores - selective, oneclick
                restore_id = ""
                for restore_test in restore_tests:
                    if (test[3] == "no_delete" and restore_test[1] == "oneclick"):
                        LOG.debug(
                            "Oneclick restore test can only be executed when instance is deleted, hence skipping.")
                    else:
                        if "_oneclickrestore_api" in restore_test[0]:
                            reporting.add_test_script(restore_test[0])
                        restore = restore_test[1]
                        LOG.debug("Perform {} restore".format(restore))

                        if restore == "oneclick":
                            restore_id = self._perform_oneclick_restore(workload_id, snapshot_id)
                        elif restore == "selective":
                            restore_id = self._perform_selective_restore([self.vm_id], self.volume_id, workload_id,
                                                                         snapshot_id)

                        restored_vms = self.get_restored_vm_list(restore_id)
                        LOG.debug("\nRestored vms : {}\n".format(restored_vms))

                        # Security group and rules verification post restore
                        LOG.debug("Compare the security groups before and after restore")
                        secgroups_after1 = self.list_security_groups()
                        if restore == "selective" and test[3] != "delete_vm_secgrp_shared" :
                            secgroups_after2 = self.list_security_groups(tenant_id_1)
                            secgroups_after = self._concat_lists(secgroups_after1,secgroups_after2)
                        else:
                            secgroups_after = secgroups_after1
                        if len(secgroups_after) == len(secgroups_before):
                            reporting.add_test_step(
                                "Security group verification pre and post restore",
                                tvaultconf.PASS,
                            )
                        else:
                            LOG.error("Security groups verification pre and post restore")
                            reporting.add_test_step(
                                "Security groups verification failed pre and post restore",
                                tvaultconf.FAIL,
                            )
                            reporting.set_test_script_status(tvaultconf.FAIL)

                        LOG.debug("Compare the security group rules before and after restore")
                        rules_after = self.list_security_group_rules()
                        if len(rules_after) == len(rules_before):
                            reporting.add_test_step(
                                "Security group rules verification pre and post restore",
                                tvaultconf.PASS,
                            )
                        else:
                            reporting.add_test_step(
                                "Security group rules verification pre and post restore",
                                tvaultconf.FAIL,
                            )
                            reporting.set_test_script_status(tvaultconf.FAIL)

                        # Verify the security group & rules assigned to the restored instance
                        LOG.debug(
                            "Comparing restored security group & rules for {}".format(
                                security_group_names_projB
                            )
                        )
                        restored_secgrps = self.getRestoredSecGroupPolicies(restored_vms)
                        LOG.debug(
                            "Comparing security group & rules assigned to the restored instances."
                        )
                        self._security_group_verification_post_restore(restored_secgrps)
                        restored_secgroup_ids = self._security_group_and_rules_verification(
                            security_group_names_projB, data_sec_group_and_rules_tenantB, rules_count
                        )

                        # Verify security group and rules for shared security group
                        restored_secgroup_ids.extend(self._security_group_and_rules_verification(
                            security_group_names_projA, data_sec_group_and_rules_tenantA, rules_count
                        ))

                        # Delete restored vms and security groups created during earlier restore
                        if test != tests[-1]:
                            LOG.debug("deleting restored vm and restored security groups and rules")
                            self._delete_vms_secgroups(restored_vms, restored_secgroup_ids)
                        reporting.test_case_to_write()

            except Exception as e:
                LOG.error("Exception: " + str(e))
                reporting.add_test_step(str(e), tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                reporting.test_case_to_write()

    # Test case automation for #OS-2029 : Shared Security_Group_Restore
    # http://192.168.15.51/testlink/linkto.php?tprojectPrefix=OS&item=testcase&id=OS-2029
    @decorators.attr(type="workloadmgr_api")
    def test_03_multilevel_shared_security_group(self):
        test_var = "tempest.api.workloadmgr.security_group.test_multilevel_shared_security_group"

        tenant_id = CONF.identity.tenant_id
        tenant_id_1 = CONF.identity.tenant_id_1

        restore_tests = [[test_var + "_selectiverestore_api", "selective"],
                         [test_var + "_oneclickrestore_api", "oneclick"]]
        reporting.add_test_script(restore_tests[0][0])
        security_group_count = 1
        rules_count = 3
        try:
            LOG.debug("Creating third project for the test")
            project_details = self.create_project(project_cleanup=True)
            LOG.debug("Created project {}".format(project_details["name"]))
            tenant_id_2 = project_details["id"]
            proj_name_2 = project_details["name"]

            LOG.debug("Create shared Security group/s with distinct rules")
            security_group_names_projA = tvaultconf.security_group_name + str(random.randint(0, 10000))
            security_group_names_projB = tvaultconf.security_group_name + str(random.randint(0, 10000))
            security_group_names_projC = tvaultconf.security_group_name + str(random.randint(0, 10000))
            try:
                # create security group in project A (tenant_id_1)
                LOG.debug(
                    "Setting project to project-A: {} and {}".format(CONF.identity.project_alt_name, tenant_id_1))
                data_sec_group_and_rules_tenantA = self._generate_data_for_secgrp(
                    security_group_count, rules_count
                )
                security_groups_tenantA = self._create_sec_groups_rule(
                    security_group_names_projA,
                    data_sec_group_and_rules_tenantA,
                    tenant_id_1
                )
                print("project A sec group id: {}".format(security_groups_tenantA[0]))
                reporting.add_test_step(
                    "creating shared security group/s {} with distinct rules in project-A ".format(
                        security_group_names_projA + str(1)),
                    tvaultconf.PASS,
                )

                # Create the RBAC policy entry using the openstack network rbac create and share the above created security_group with project-B
                rbac_command = command_argument_string.rbac_create_secgroup + tenant_id_2 + " --action access_as_shared --type security_group " + \
                               security_groups_tenantA[0]
                LOG.debug("rbac command: {}".format(rbac_command))
                rc = cli_parser.cli_returncode(rbac_command)
                if rc != 0:
                    reporting.add_test_step(
                        "Execute create rbac policy for security group {}".format(security_group_names_projA + str(1)),
                        tvaultconf.FAIL,
                    )
                    raise Exception("rbac command did not execute correctly")
                else:
                    reporting.add_test_step(
                        "Execute create rbac policy for security group {}".format(security_group_names_projA + str(1)),
                        tvaultconf.PASS,
                    )
                time.sleep(10)

                # Create security group in project-B (tenant_id)
                LOG.debug("Setting project to project-B: {} and {}".format(proj_name_2, tenant_id_2))
                data_sec_group_and_rules_tenantB = self._generate_data_for_secgrp(
                    security_group_count, rules_count
                )
                security_groups_tenantB = self._create_sec_groups_rule(
                    security_group_names_projB,
                    data_sec_group_and_rules_tenantB,
                    tenant_id_2
                )
                print("project B sec group id: {}".format(security_groups_tenantB[0]))

                # create security_group_rule for the sec_group created in above step, attach the remote-sec-group as the shared sec_group.
                LOG.debug("Create security group rule with shared security group")
                self.add_security_group_rule(
                    parent_grp_id=security_groups_tenantB[0],
                    remote_grp_id=security_groups_tenantA[0],
                    ip_proto="tcp",
                    from_prt=1567,
                    to_prt=3269,
                )
                reporting.add_test_step(
                    "creating security group/s {} with shared security group from project-B ".format(
                        security_group_names_projB + str(1)),
                    tvaultconf.PASS,
                )

                # Create the RBAC policy entry using the openstack network rbac create and share the above created security_group with project-B
                rbac_command = command_argument_string.rbac_create_secgroup + tenant_id + " --action access_as_shared --type security_group " + \
                               security_groups_tenantB[0]
                LOG.debug("rbac command: {}".format(rbac_command))
                rc = cli_parser.cli_returncode(rbac_command)
                if rc != 0:
                    reporting.add_test_step(
                        "Execute create rbac policy for security group {}".format(security_group_names_projB + str(1)),
                        tvaultconf.FAIL,
                    )
                    raise Exception("rbac command did not execute correctly")
                else:
                    reporting.add_test_step(
                        "Execute create rbac policy for security group {}".format(security_group_names_projB + str(1)),
                        tvaultconf.PASS,
                    )
                time.sleep(10)

                # Create security group in project-C (tenant_id)
                LOG.debug("Setting project to project-C: {} and {}".format(CONF.identity.project_name, tenant_id))
                data_sec_group_and_rules_tenantC = self._generate_data_for_secgrp(
                    security_group_count, rules_count
                )
                security_groups_tenantC = self._create_sec_groups_rule(
                    security_group_names_projC,
                    data_sec_group_and_rules_tenantC,
                )
                print("project C sec group id: {}".format(security_groups_tenantC[0]))

                # create security_group_rule for the sec_group created in above step, attach the remote-sec-group as the shared sec_group.
                LOG.debug("Create security group rule with shared security group")
                self.add_security_group_rule(
                    parent_grp_id=security_groups_tenantC[0],
                    remote_grp_id=security_groups_tenantB[0],
                    ip_proto="tcp",
                    from_prt=3487,
                    to_prt=9659,
                )
                reporting.add_test_step(
                    "creating security group/s {} with shared security group from project-C ".format(
                        security_group_names_projC + str(1)),
                    tvaultconf.PASS,
                )

            except Exception as e:
                LOG.error(f"Exception: {e}")
                raise Exception("Shared security group and rules creation failed")

            # Create an image booted instance with Security group and attach an volume.
            LOG.debug(
                "Create an image booted instance with Security group and attach an volume"
            )
            # Create volume
            self.volume_id = self.create_volume(volume_cleanup=True)
            LOG.debug("Volume ID: " + str(self.volume_id))

            # create vm
            self.vm_id = self.create_vm(
                security_group_id=security_groups_tenantC[0], vm_cleanup=True
            )
            LOG.debug("Vm ID: " + str(self.vm_id))

            # Attach volume to the instance
            self.attach_volume(self.volume_id, self.vm_id, attach_cleanup=True)
            LOG.debug("Volume attached")

            # Create a workload for the instance.
            LOG.debug("Create a workload for this instance.")
            workload_id = self._create_workload([self.vm_id])
            LOG.debug("\nWorkload created : {}\n".format(workload_id))

            # Take a Full snapshot
            LOG.debug("Take a full snapshot")
            snapshot_id = self._take_full_snapshot(workload_id)

            # Get the sec groups and rules list for verification post restore
            secgroups_before1 = self.list_security_groups()
            secgroups_before2 = self.list_security_groups(tenant_id_1)
            secgroups_before3 = self.list_security_groups(tenant_id_2)
            rules_before = self.list_security_group_rules()

            secgroups_before = self._concat_lists(secgroups_before1, secgroups_before2, secgroups_before3)
            LOG.debug("Security groups before : {}".format(secgroups_before))
            LOG.debug("Security group rules before : {}".format(rules_before))

            # Delete vm, volumes, security groups as per the test step
            try:
                vol = []
                for vm in [self.vm_id]:
                    LOG.debug("Get list of all volumes to be deleted from instance {}".format(vm))
                    vol.append(self.get_attached_volumes(vm))
                self.delete_vms([self.vm_id])
                LOG.debug("Delete volumes: {}".format(vol))
                self.delete_volumes(vol)
                reporting.add_test_step("Deleted vm {} before proceeding with restore".format(self.vm_id),
                                        tvaultconf.PASS, )
                time.sleep(10)

                # Delete security group assigned to instance and shared security group
                delete_secgrp_ids = [security_groups_tenantA[0], security_groups_tenantB[0], security_groups_tenantC[0]]
                for secgrp in delete_secgrp_ids:
                    self.delete_security_group(secgrp)
                    LOG.debug(
                        "Delete security group assigned to instance and shared security group: {}".format(
                            secgrp))
                reporting.add_test_step(
                    "Deleted security groups/shared security group {} before proceeding with restore".format(
                        delete_secgrp_ids),
                    tvaultconf.PASS, )

            except Exception as e:
                LOG.error(f"Exception: {e}")
                raise Exception("Deletion of vms/security group/Shared security group failed")

            # Perform restores - selective, oneclick

            restore_id = ""
            for restore_test in restore_tests:
                # restored_secgroup_ids = []
                if "_oneclickrestore_api" in restore_test[0]:
                    reporting.add_test_script(restore_test[0])
                restore = restore_test[1]
                LOG.debug("Perform {} restore".format(restore))

                if restore == "oneclick":
                    restore_id = self._perform_oneclick_restore(workload_id, snapshot_id)
                elif restore == "selective":
                    restore_id = self._perform_selective_restore([self.vm_id], self.volume_id, workload_id,
                                                                 snapshot_id)

                restored_vms = self.get_restored_vm_list(restore_id)
                LOG.debug("\nRestored vms : {}\n".format(restored_vms))

                # Security group and rules verification post restore
                LOG.debug("Compare the security groups before and after restore")
                secgroups_after = self.list_security_groups()
                if len(secgroups_after) == len(secgroups_before):
                    reporting.add_test_step(
                        "Security group verification pre and post restore",
                        tvaultconf.PASS,
                    )
                else:
                    LOG.error("Security groups verification pre and post restore")
                    reporting.add_test_step(
                        "Security groups verification failed pre and post restore",
                        tvaultconf.FAIL,
                    )
                    reporting.set_test_script_status(tvaultconf.FAIL)

                LOG.debug("Compare the security group rules before and after restore")
                rules_after = self.list_security_group_rules()
                if len(rules_after) == len(rules_before):
                    reporting.add_test_step(
                        "Security group rules verification pre and post restore",
                        tvaultconf.PASS,
                    )
                else:
                    reporting.add_test_step(
                        "Security group rules verification pre and post restore",
                        tvaultconf.FAIL,
                    )
                    reporting.set_test_script_status(tvaultconf.FAIL)

                # Verify the security group & rules assigned to the restored instance
                LOG.debug(
                    "Comparing restored security group & rules for {}".format(
                        security_group_names_projB
                    )
                )
                restored_secgrps = self.getRestoredSecGroupPolicies(restored_vms)
                LOG.debug(
                    "Comparing security group & rules assigned to the restored instances."
                )
                self._security_group_verification_post_restore(restored_secgrps)
                restored_secgroup_ids = self._security_group_and_rules_verification(
                    security_group_names_projC, data_sec_group_and_rules_tenantC, rules_count
                )

                # Verify security group and rules for shared security group
                restored_secgroup_ids.extend(self._security_group_and_rules_verification(
                    security_group_names_projB, data_sec_group_and_rules_tenantB, rules_count
                ))

                # Verify security group and rules for shared security group
                restored_secgroup_ids.extend(self._security_group_and_rules_verification(
                    security_group_names_projA, data_sec_group_and_rules_tenantA, rules_count
                ))
                LOG.debug("Check if restored security groups and rules {} are present".format(restored_secgroup_ids))

                # Delete restored vms and security groups created during earlier restore
                # if restore_test != restore_tests[-1]:
                LOG.debug("deleting restored vm and restored security groups and rules")
                self._delete_vms_secgroups(restored_vms, restored_secgroup_ids)
                reporting.test_case_to_write()


        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
