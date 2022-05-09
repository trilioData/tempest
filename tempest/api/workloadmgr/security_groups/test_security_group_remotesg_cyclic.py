import os
import random
import sys
import time

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
    credentials = ["primary"]
    restored_secgroup_ids = []

    def _create_vms_with_secgroup(self, sec_group, vm_count=1):
        vms = []
        boot_vols = []
        for each in range(1, vm_count + 1):
            boot_volume_id = self.create_volume(
                size=tvaultconf.bootfromvol_vol_size,
                image_id=CONF.compute.image_ref,
                volume_cleanup=True,
            )
            boot_vols.append(boot_volume_id)
            self.set_volume_as_bootable(boot_volume_id)
            LOG.debug("Bootable Volume ID : " + str(boot_volume_id))

            block_mapping_details = [
                {
                    "source_type": "volume",
                    "delete_on_termination": "false",
                    "boot_index": 0,
                    "uuid": boot_volume_id,
                    "destination_type": "volume",
                }
            ]
            # Create instance
            vm_id = self.create_vm(
                security_group_id=sec_group,
                block_mapping_data=block_mapping_details,
                vm_cleanup=True,
            )
            LOG.debug("VM ID : " + str(vm_id))
            vms.append(vm_id)
        return vms

    def _attach_empty_volume(self, vms):
        for vm in vms:
            volume_id = self.create_volume(volume_cleanup=True)
            LOG.debug("Volume ID: " + str(volume_id))
            self.attach_volume(volume_id, vm, attach_cleanup=True)
            LOG.debug("Volume attached")
        return vms

    def _create_workload(self, vms):
        LOG.debug("\nvms : {}\n".format(vms))
        workload_id = self.workload_create(
            instances=vms,
            workload_type=tvaultconf.parallel,
            workload_name="for_remote_secgrp",
            workload_cleanup=True,
        )
        LOG.debug("Workload ID: " + str(workload_id))
        if workload_id is not None:
            self.wait_for_workload_tobe_available(workload_id)
            if self.getWorkloadStatus(workload_id) == "available":
                reporting.add_test_step(
                    "Create workload", tvaultconf.PASS
                )
        else:
            raise Exception("Workload creation failed")
        return workload_id

    def _take_full_snapshot(self, workload_id):
        snapshot_id = self.workload_snapshot(
            workload_id, True, snapshot_cleanup=True
        )
        time.sleep(5)
        self.wait_for_workload_tobe_available(workload_id)
        if self.getSnapshotStatus(workload_id, snapshot_id) == "available":
            reporting.add_test_step(
                "Create full snapshot", tvaultconf.PASS
            )
            LOG.debug("Full snapshot available!!")
        else:
            raise Exception("Snapshot creation failed")
        LOG.debug("\nFull snapshot ids : {}\n".format(snapshot_id))
        return snapshot_id

    def _perform_oneclick_restore(self, workload_id, snapshot_id):
        restore_id = self.snapshot_restore(
            workload_id, snapshot_id, restore_cleanup=True
        )
        self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
        if (
                self.getRestoreStatus(workload_id, snapshot_id, restore_id)
                == "available"
        ):
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

    def _perform_selective_restore(self, vms, volumes, workload_id, snapshot_id):
        rest_details = {}
        rest_details['rest_type'] = 'selective'
        rest_details['network_id'] = CONF.network.internal_network_id
        rest_details['subnet_id'] = self.get_subnet_id(
            CONF.network.internal_network_id)
        rest_details['instances'] = {vms[0]: volumes}

        payload = self.create_restore_json(rest_details)
        # Trigger selective restore of full snapshot
        restore_id = self.snapshot_selective_restore(
            workload_id, snapshot_id,
            restore_name=tvaultconf.selective_restore_name,
            restore_cleanup=True,
            instance_details=payload['instance_details'],
            network_details=payload['network_details'])

        if (self.getRestoreStatus(workload_id, snapshot_id, restore_id) == "available"):
            reporting.add_test_step(
                "Selective restore completed successfully", tvaultconf.PASS)
            LOG.debug('selective restore passed')
        else:
            reporting.add_test_step(
                "Selective restore failed", tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
            LOG.error('selective restore failed')
        return restore_id

    def _restore_through_wlm_cli(self, snapshot_id):
        restore_command = (
                command_argument_string.restore_security_groups + " " + snapshot_id
        )
        rc = cli_parser.cli_returncode(restore_command)
        if rc != 0:
            reporting.add_test_step(
                "Execute restore security groups command", tvaultconf.FAIL
            )
            raise Exception("Command did not execute correctly")
        else:
            reporting.add_test_step(
                "Execute restore security groups command", tvaultconf.PASS
            )
            LOG.debug("Command executed correctly")

        time.sleep(10)
        # DB verification of the command execution
        wc = query_data.get_snapshot_restore_status(
            tvaultconf.security_group_restore_name, snapshot_id
        )
        LOG.debug("Security group restore status: " + str(wc))
        while str(wc) != "available" or str(wc) != "error":
            time.sleep(5)
            wc = query_data.get_snapshot_restore_status(
                tvaultconf.security_group_restore_name, snapshot_id
            )
            LOG.debug("Snapshot restore status: " + str(wc))
            if str(wc) == "available":
                reporting.add_test_step(
                    "Security group restore command verification",
                    tvaultconf.PASS,
                )
                break
            else:
                reporting.add_test_step(
                    "security group restore command verification",
                    tvaultconf.FAIL,
                )
                reporting.set_test_script_status(tvaultconf.FAIL)
                break

    def _generate_data_for_secgrp(self, security_group_count, rules_count):
        secgrp_list_with_rules = []
        ip_protocols = ["tcp", "udp"]
        for t in range(1, security_group_count + 1):
            instance_attached_rules_dict = []
            for i in range(0, rules_count):
                protocol = random.choice(ip_protocols)
                from_port = random.randrange(1500, 2700)
                to_port = random.randrange(2800, 3999)
                values = {
                    "protocol": protocol,
                    "port_range_min": from_port,
                    "port_range_max": to_port,
                }
                instance_attached_rules_dict.append(values)
            secgrp_list_with_rules.append(instance_attached_rules_dict)
        LOG.debug("sec group + rules: {}".format(secgrp_list_with_rules))
        return secgrp_list_with_rules

    """ Method to create Security groups P, Q, R with distinct rules and assign the relationship like P -> Q -> R -> P """

    def _create_sec_groups_rule(self, secgrp_name, data_sec_group_and_rules):
        LOG.debug("Create security group and rule")
        created_sec_groups = []
        for each in range(1, len(data_sec_group_and_rules) + 1):
            sgid = self.create_security_group(
                name=secgrp_name + format(each),
                description="security group containing remote security group",
                secgrp_cleanup=True,
            )
            created_sec_groups.append(sgid)
            # Delete default security group rules
            self.delete_default_rules(sgid)
        for t in range(0, len(created_sec_groups)):
            LOG.debug(
                "Creating rule with other details and remote group id in fashion P -> Q -> R "
            )
            secgrp = created_sec_groups[t]
            remote_secgrp = created_sec_groups[t - 1]
            remote_sec_flag = True
            # These security group will have atleast one remote sg/cyclic sg
            for each in data_sec_group_and_rules[t]:
                LOG.debug("Print element like: {}".format(each["port_range_min"]))
                if remote_sec_flag == True:
                    self.add_security_group_rule(
                        parent_grp_id=secgrp,
                        remote_grp_id=remote_secgrp,
                        ip_proto=each["protocol"],
                        from_prt=each["port_range_min"],
                        to_prt=each["port_range_max"],
                    )
                    remote_sec_flag = False
                else:
                    self.add_security_group_rule(
                        parent_grp_id=secgrp,
                        ip_proto=each["protocol"],
                        from_prt=each["port_range_min"],
                        to_prt=each["port_range_max"],
                    )
        LOG.debug(
            "Security groups collection: {} and last entry {}".format(
                created_sec_groups, created_sec_groups[-1]
            )
        )
        return created_sec_groups

    def _security_group_verification_post_restore(self, restored_secgrps):
        for restored_secgrp in restored_secgrps:
            LOG.debug(
                "Print names of restored security groups : {}".format(
                    restored_secgrp["name"]
                )
            )
            if self.verifySecurityGroupsByname(restored_secgrp["name"]):
                reporting.add_test_step(
                    "Security group verification successful for restored vm {}".format(
                        restored_secgrp["name"]
                    ),
                    tvaultconf.PASS,
                )
            else:
                reporting.add_test_step(
                    "Security group verification failed for restored vm {}".format(
                        restored_secgrp["name"]
                    ),
                    tvaultconf.FAIL,
                )
                reporting.set_test_script_status(tvaultconf.FAIL)

    def _rules_verification_post_restore(self, security_group_names, data_sec_group_and_rules, rules_count):
        for t in range(0, len(data_sec_group_and_rules)):
            restored_security_group = security_group_names + str(t + 1)
            sgid = self.get_security_group_id_by_name(restored_security_group)
            # restored security groups to be cleaned after the execution
            self.restored_secgroup_ids.append(sgid)
            rule_list = self.list_secgroup_rules_for_secgroupid(sgid)
            count = 0

            for each in data_sec_group_and_rules[t]:
                for rule in rule_list:
                    result = self.verifySecurityGroupRules(rule["id"], sgid, each)
                    if result == True:
                        count += 1
                LOG.debug(
                    "Here is the count: {} for restored rules per security group {}".format(
                        count, each
                    )
                )

            if count == rules_count * 2:
                reporting.add_test_step(
                    "Security group rules verification successful for restored secgroup {}".format(
                        restored_security_group
                    ),
                    tvaultconf.PASS,
                )
            else:
                reporting.add_test_step(
                    "Security group rules verification failed for restored secgroup {}".format(
                        restored_security_group
                    ),
                    tvaultconf.FAIL,
                )
                reporting.set_test_script_status(tvaultconf.FAIL)


    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    # Test case OS-1683 : Security_Group_Restore_1
    # http://192.168.15.51/testlink/linkto.php?tprojectPrefix=OS&item=testcase&id=OS-1683
    @decorators.attr(type="workloadmgr_api")
    def test_with_samerule(self):
        try:
            # Verification of cyclic security group restore with same rules
            LOG.debug("\nStarted test execution: ")
            reporting.add_test_script(
                "tempest.api.workloadmgr.security_groups.test_security_group_remotesg_cyclic.test_with_samerule"
            )

            security_group_names_list = [
                "test_secgroups-PQR",
                "test_secgroups-ABC",
                "test_secgroups-XYZ",
            ]
            security_group_count = 3
            rules_count = 2

            # 1. Create Security groups P, Q, R with distinct rules and assign the relationship like P -> Q -> R -> P
            LOG.debug(
                "\nCreate Security groups P, Q, R with distinct rules and assign the relationship like P -> Q -> R -> P"
            )
            data_sg_same_rule = self._generate_data_for_secgrp(
                security_group_count, rules_count
            )
            sec_groups_id_PQR = self._create_sec_groups_rule(
                security_group_names_list[0], data_sg_same_rule
            )

            # 2. Create an image booted instance with Security group P and attach an empty volume.
            LOG.debug(
                "Create an image booted instance with Security group P and attach an empty volume."
            )
            vms = self._create_vms_with_secgroup(sec_groups_id_PQR[0])
            LOG.debug("\nVMs : {}\n".format(vms))
            vms = self._attach_empty_volume(vms)
            LOG.debug("\nEmpty Volume attached : {}\n".format(vms))

            # 3. Create a workload for the instance.
            LOG.debug("Create a workload for this instance.")
            workload_id = self._create_workload(vms)
            LOG.debug("\nWorkload created : {}\n".format(workload_id))

            # 4. Take a Full snapshot
            LOG.debug("Take a full snapshot")
            snapshot_id = self._take_full_snapshot(workload_id)

            # 5. Delete vms, volumes, security groups
            self.delete_vm_secgroups(vms, sec_groups_id_PQR)
            time.sleep(60)

            # 6. Create security groups A, B, C with different rules other than P, Q, R and assign relationship A -> B -> C -> A
            LOG.debug(
                "Create security groups A, B, C with different rules other than P, Q, R and assign relationship A -> B -> C -> A"
            )
            data_sg_diff_rule = self._generate_data_for_secgrp(
                security_group_count, rules_count
            )
            self._create_sec_groups_rule(security_group_names_list[1], data_sg_diff_rule)

            # 7. Create security groups X, Y, Z with same rules as that of P, Q, R and assign relationship X -> Y -> Z -> X
            LOG.debug(
                "Create security groups X, Y, Z with same rules as that of P, Q, R and assign relationship X -> Y -> Z -> X"
            )
            sec_groups_id_XYZ = self._create_sec_groups_rule(
                security_group_names_list[2], data_sg_same_rule
            )
            secgroups_before = self.list_security_groups()
            rules_before = self.list_security_group_rules()

            # 8. Perform one click restore
            LOG.debug("Perform one click restore")
            restore_id = self._perform_oneclick_restore(workload_id, snapshot_id)

            restored_vms = self.get_restored_vm_list(restore_id)
            LOG.debug("\nRestored vms : {}\n".format(restored_vms))

            # 9. Compare the security groups and rules before and after restore
            LOG.debug("Compare the security groups before and after restore")
            secgroups_after = self.list_security_groups()
            if secgroups_after == secgroups_before:
                reporting.add_test_step(
                    "Security group verification successful pre and post restore",
                    tvaultconf.PASS,
                )
            else:
                reporting.add_test_step(
                    "Security groups verification failed ",
                    tvaultconf.FAIL,
                )
                reporting.set_test_script_status(tvaultconf.FAIL)

            LOG.debug("Compare the security group rules before and after restore")
            rules_after = self.list_security_group_rules()
            if rules_after == rules_before:
                reporting.add_test_step(
                    "Security group rules verification successful pre and post restore",
                    tvaultconf.PASS,
                )
            else:
                reporting.add_test_step(
                    "Security group rules verification failed ",
                    tvaultconf.FAIL,
                )
                reporting.set_test_script_status(tvaultconf.FAIL)

            # 10. Verify the security group assigned to the restored instance
            LOG.debug("Comparing security group & rules assigned to the restored instances.")
            assigned_secgrps = self.getRestoredSecGroupPolicies(restored_vms)
            if assigned_secgrps == None:
                raise Exception("Security group is not attached to restored vm")
            else:
                reporting.add_test_step(
                    "Security group {} is attached to restored vm".format(assigned_secgrps),
                    tvaultconf.PASS,
                )

            # 11. Comparing security group and rules for security group assigned to the restored instances.
            LOG.debug(
                "Comparing security group & rules assigned to the restored instances."
            )
            self._security_group_verification_post_restore(assigned_secgrps)
            self._rules_verification_post_restore(security_group_names_list[2], data_sg_same_rule, rules_count)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()

    # Test case OS-1684 : Security_Group_Restore_2
    # http://192.168.15.51/testlink/linkto.php?tprojectPrefix=OS&item=testcase&id=OS-1684
    @decorators.attr(type="workloadmgr_api")
    def test_with_diffrule(self):
        try:
            # Verification of cyclic security group restore with different rules
            reporting.add_test_script(
                "tempest.api.workloadmgr.security_groups.test_security_group_remotesg_cyclic.test_with_diffrule"
            )

            security_group_names = "test_secgroups_diff_rules-"
            security_group_count = 3
            rules_count = 2

            # 1. Create Security groups P, Q, R with distinct rules and assign the relationship like P -> Q -> R -> P
            LOG.debug(
                "\nCreate Security groups P, Q, R with distinct rules and assign the relationship like P -> Q -> R -> P"
            )
            data_sec_group_and_rules = self._generate_data_for_secgrp(security_group_count, rules_count)
            sec_groups_id_PQR = self._create_sec_groups_rule(security_group_names, data_sec_group_and_rules)

            # 2. Create an image booted instance with Security group P and attach an empty volume.
            LOG.debug(
                "Create an image booted instance with Security group P and attach an empty volume."
            )
            vms = self._create_vms_with_secgroup(sec_groups_id_PQR[0])
            LOG.debug("\nVMs : {}\n".format(vms))
            vms = self._attach_empty_volume(vms)
            LOG.debug("\nEmpty Volume attached : {}\n".format(vms))

            # 3. Create a workload for the instance.
            LOG.debug("Create a workload for this instance.")
            workload_id = self._create_workload(vms)
            LOG.debug("\nWorkload created : {}\n".format(workload_id))

            # 4. Take a Full snapshot
            LOG.debug("Take a full snapshot")
            snapshot_id = self._take_full_snapshot(workload_id)

            secgroups_before = self.list_security_groups()
            rules_before = self.list_security_group_rules()

            # 5. Delete vms, volumes, security groups
            LOG.debug("Delete VM + volume + security groups (P, Q, R)")
            self.delete_vm_secgroups(vms, sec_groups_id_PQR)
            time.sleep(60)

            # 6. Perform one click restore
            LOG.debug("Perform one click restore")
            restore_id = self._perform_oneclick_restore(workload_id, snapshot_id)

            restored_vms = self.get_restored_vm_list(restore_id)
            LOG.debug("\nRestored vms : {}\n".format(restored_vms))

            # 7. Compare the security groups and rules before and after restore
            LOG.debug("Compare the security groups before and after restore")
            secgroups_after = self.list_security_groups()
            if len(secgroups_after) == len(secgroups_before):
                reporting.add_test_step(
                    "Security group verification successful pre and post restore",
                    tvaultconf.PASS,
                )
            else:
                reporting.add_test_step(
                    "Security groups verification failed ",
                    tvaultconf.FAIL,
                )
                reporting.set_test_script_status(tvaultconf.FAIL)

            LOG.debug("Compare the security group rules before and after restore")
            rules_after = self.list_security_group_rules()
            if len(rules_after) == len(rules_before):
                reporting.add_test_step(
                    "Security group rules verification successful pre and post restore",
                    tvaultconf.PASS,
                )
            else:
                reporting.add_test_step(
                    "Security group rules verification failed ",
                    tvaultconf.FAIL,
                )
                reporting.set_test_script_status(tvaultconf.FAIL)

            # 8. Verify the security group & rules assigned to the restored instance
            restored_secgrps = self.getRestoredSecGroupPolicies(restored_vms)
            LOG.debug(
                "Comparing security group & rules assigned to the restored instances."
            )
            self._security_group_verification_post_restore(restored_secgrps)

            # 9. Compare rules for restored/instance attached security groups
            self._rules_verification_post_restore(security_group_names, data_sec_group_and_rules, rules_count)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()
            if len(restored_secgroup_ids) != 0:
                for secgrp in restored_secgroup_ids:
                    LOG.debug("Deleting security groups: {}".format(secgrp))
                    self.delete_security_group(secgrp)

    # Test case #OS-1685 : Security_Group_Restore_3
    # http://192.168.15.51/testlink/linkto.php?tprojectPrefix=OS&item=testcase&id=OS-1685
    @decorators.attr(type="workloadmgr_api")
    def test_with_cyclicsg_01(self):
        try:
            reporting.add_test_script("tempest.api.workloadmgr.security_groups.test_security_group_remotesg_cyclic.vol_attach_vm")

            security_group_names = tvaultconf.security_group_name
            security_group_count = 3
            rules_count = 3
            delete_secgrp = [security_group_names + str(2)]

            LOG.debug(
                "\nCreate Security groups P, Q, R with distinct rules and assign the relationship like P -> Q -> R -> P"
            )
            data_sec_group_and_rules = self._generate_data_for_secgrp(security_group_count, rules_count)
            created_sec_groups = self._create_sec_groups_rule(security_group_names, data_sec_group_and_rules)
            if (data_sec_group_and_rules != None and created_sec_groups != None):
                reporting.add_test_step("creating security groups P, Q, R and rules", tvaultconf.PASS)
            else:
                reporting.add_test_step("creating security groups P, Q, R and rules", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            LOG.debug(
                "Create an image booted instance with Security group P,Q,R and attach an volume."
            )
            vms = self._create_vms_with_secgroup(created_sec_groups[0])
            # vms= ["d7fa6302-e828-4dca-b59e-2e46474416f6"]
            LOG.debug("\nVMs : {}\n".format(vms))
            volumes = self._attach_empty_volume(vms)
            LOG.debug("\nEmpty Volume attached : {}\n".format(vms))

            # Assign additional security groups if provided
            LOG.debug("Sec groups before adding to instance: {}".format(created_sec_groups))
            for i in range(1, security_group_count):
                result = self.add_security_group_to_instance(vms[0], created_sec_groups[i])
                if result == False:
                    raise Exception("Add security group to instance failed")
            LOG.debug("Assigned all security groups to instance")

            LOG.debug("Create a workload for this instance.")
            workload_id = self._create_workload(vms)
            LOG.debug("\nWorkload created : {}\n".format(workload_id))

            # Take a Full snapshot
            LOG.debug("Take a full snapshot")
            snapshot_id = self._take_full_snapshot(workload_id)

            secgroups_before = self.list_security_groups()
            rules_before = self.list_security_group_rules()

            # Delete original vms, volumes, security groups Q before restore
            LOG.debug("Delete VM + volume + security group Q before restore")
            try:
                secgrp_ids_tobe_deleted = [[el] for el in created_sec_groups]
                self.delete_vm_secgroups(vms, secgrp_ids_tobe_deleted[1])
                reporting.add_test_step(
                    "Delete vm and security group Q", tvaultconf.PASS
                )
            except Exception as e:
                LOG.error(f"Exception: {e}")
                raise Exception("Deletion of vm and security group/s failed")
            time.sleep(60)

            # Trigger selective restore
            restore_id = self._perform_selective_restore(vms, volumes, workload_id, snapshot_id)
            restored_vms = self.get_restored_vm_list(restore_id)
            LOG.debug("\nRestored vms : {}\n".format(restored_vms))
            restored_secgrps = self.getRestoredSecGroupPolicies(restored_vms)
            LOG.debug("Get the restored security groups: {}".format(restored_secgrps))

            # Compare the security groups and rules before and after restore
            secgroups_after = self.list_security_groups()
            if len(secgroups_after) != len(secgroups_before):
                LOG.error("Compare the security groups before and after selective restore")
                reporting.add_test_step(
                    "Compare the security groups before and after selective restore",
                    tvaultconf.FAIL,
                )
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Compare the security groups before and after selective restore",
                    tvaultconf.PASS,
                )

            rules_after = self.list_security_group_rules()
            if len(rules_after) != len(rules_before):
                LOG.error("Compare the security group rules before and after selective restore")
                reporting.add_test_step(
                    "Compare the security group rules before and after selective restore",
                    tvaultconf.FAIL,
                )
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Compare the security group rules before and after selective restore",
                    tvaultconf.PASS,
                )

            # Compare the security group & rules assigned to the restored instance
            LOG.debug("Comparing restored security group & rules for {}".format(delete_secgrp))
            for restored_secgrp in restored_secgrps:
                if self.verifySecurityGroupsByname(restored_secgrp["name"]):
                    reporting.add_test_step(
                        "Security group {} present after selective restore".format(restored_secgrp["name"]),
                        tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Security group {} NOT present after selective restore".format(restored_secgrp["name"]),
                        tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
                # Check for deleted security group
                for each in delete_secgrp:
                    if each == restored_secgrp["name"]:
                        reporting.add_test_step(
                            "Deleted Security group {} is restored after selective restore".format(each),
                            tvaultconf.PASS)
                    else:
                        reporting.add_test_step(
                            "Deleted Security group {} is NOT restored after selective restore".format(each),
                            tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)

            self._rules_verification_post_restore(security_group_names, data_sec_group_and_rules, rules_count)

             # Delete restored vms and security groups created during selective restore
            try:
                LOG.debug("deleting restored vm and restored security groups and rules")
                self.delete_vm_secgroups(restored_vms, restored_secgrps)
                reporting.add_test_step(
                    "Delete restored vm and restored security groups before proceeding with onelick restore", tvaultconf.PASS
                )
            except Exception as e:
                LOG.error(f"Exception: {e}")
                raise Exception("Deletion of vm and security group/s failed")
            time.sleep(60)

            # Perform one click restore
            LOG.debug("Perform one click restore")
            restore_id = self._perform_oneclick_restore(workload_id, snapshot_id)

            restored_vms = self.get_restored_vm_list(restore_id)
            LOG.debug("\nRestored vms : {}\n".format(restored_vms))
            restored_secgrps = self.getRestoredSecGroupPolicies(restored_vms)
            LOG.debug("Get the restored security groups: {}".format(restored_secgrps))

            # Compare the security groups and rules before and after restore
            LOG.debug("Compare the security groups before and after Oneclick restore")
            secgroups_after = self.list_security_groups()
            if len(secgroups_after) == len(secgroups_before):
                reporting.add_test_step(
                    "Compare the security groups before and after oneclick restore",
                    tvaultconf.PASS,
                )
            else:
                reporting.add_test_step(
                    "Compare the security groups before and after oneclick restore",
                    tvaultconf.FAIL,
                )
                reporting.set_test_script_status(tvaultconf.FAIL)

            LOG.debug("Compare the security group rules before and after oneclick restore")
            rules_after = self.list_security_group_rules()
            if len(rules_after) == len(rules_before):
                reporting.add_test_step(
                    "Compare the security group rules before and after oneclick restore",
                    tvaultconf.PASS,
                )
            else:
                reporting.add_test_step(
                    "Compare the security group rules before and after oneclick restore",
                    tvaultconf.FAIL,
                )
                reporting.set_test_script_status(tvaultconf.FAIL)

            # Compare the security group & rules assigned to the restored instance after oneclick restore
            LOG.debug("Verify restored security group & rules for {} after oneclick restore".format(delete_secgrp))
            for restored_secgrp in restored_secgrps:
                if self.verifySecurityGroupsByname(restored_secgrp["name"]):
                    reporting.add_test_step(
                        "Security group {} present after oneclick restore".format(restored_secgrp["name"]),
                        tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Security group {} NOT present after oneclick restore".format(restored_secgrp["name"]),
                        tvaultconf.FAIL)

                # Check for deleted security group
                for each in delete_secgrp:
                    if each == restored_secgrp["name"]:
                        reporting.add_test_step(
                            "Deleted Security group {} is restored after oneclick restore".format(each),
                            tvaultconf.PASS)
                    else:
                        reporting.add_test_step(
                            "Deleted Security group {} is NOT restored after oneclick restore".format(each),
                            tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)

            self._rules_verification_post_restore(security_group_names, data_sec_group_and_rules, rules_count)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()
            if len(restored_secgroup_ids) != 0:
                for secgrp in restored_secgroup_ids:
                    LOG.debug("Deleting security groups: {}".format(secgrp))
                    self.delete_security_group(secgrp)

    # Test case #OS-1895 : Security_Group_Restore_using_CLI_for_cyclic_group
    # http://192.168.15.51/testlink/linkto.php?tprojectPrefix=OS&item=testcase&id=OS-1895
    @decorators.attr(type="workloadmgr_cli")
    def test_with_cyclicsg_02(self):
        try:
            reporting.add_test_script("tempest.api.workloadmgr.security_groups.test_security_group_remotesg_cyclic.cli_restore")

            security_group_names = tvaultconf.security_group_name
            security_group_count = 3
            rules_count = 3

            LOG.debug(
                "\nCreate Security groups P, Q, R with distinct rules and assign the relationship like P -> Q -> R -> P"
            )
            data_sec_group_and_rules = self._generate_data_for_secgrp(security_group_count, rules_count)
            created_sec_groups = self._create_sec_groups_rule(security_group_names, data_sec_group_and_rules)
            if (data_sec_group_and_rules != None and created_sec_groups != None):
                reporting.add_test_step("creating security groups P, Q, R and rules", tvaultconf.PASS)
            else:
                reporting.add_test_step("creating security groups P, Q, R and rules", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            LOG.debug(
                "Create an image booted instance with Security group P,Q,R and attach an volume."
            )
            vms = self._create_vms_with_secgroup(created_sec_groups[0])
            # vms= ["d7fa6302-e828-4dca-b59e-2e46474416f6"]
            LOG.debug("\nVMs : {}\n".format(vms))
            volumes = self._attach_empty_volume(vms)
            LOG.debug("\nEmpty Volume attached : {}\n".format(vms))

            LOG.debug("Create a workload for this instance.")
            workload_id = self._create_workload(vms)
            LOG.debug("\nWorkload created : {}\n".format(workload_id))

            # Take a Full snapshot
            LOG.debug("Take a full snapshot")
            snapshot_id = self._take_full_snapshot(workload_id)

            secgroups_before = self.list_security_groups()
            rules_before = self.list_security_group_rules()

            # Delete original vms, volumes, security groups Q before restore
            LOG.debug("Delete VM + volume + cyclic security groups before restore")
            try:
                LOG.debug("Delete VM + volume + security groups")
                self.delete_vm_secgroups(vms, created_security_groups)
                reporting.add_test_step(
                    "Delete vm and security group", tvaultconf.PASS
                )
            except Exception as e:
                LOG.error(f"Exception: {e}")
                raise Exception("Deletion of vm and security group/s failed")
            time.sleep(60)

            # Perform security groups restore through wlm command
            self._restore_through_wlm_cli(snapshot_id)

            # Compare the security groups and rules before and after restore
            secgroups_after = self.list_security_groups()
            if len(secgroups_after) != len(secgroups_before):
                LOG.error("Compare the security groups before and after commandline restore")
                reporting.add_test_step(
                    "Compare the security groups before and after commandline restore",
                    tvaultconf.FAIL,
                )
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Compare the security groups before and after commandline restore",
                    tvaultconf.PASS,
                )

            rules_after = self.list_security_group_rules()
            if len(rules_after) != len(rules_before):
                LOG.error("Compare the security group rules before and after commandline restore")
                reporting.add_test_step(
                    "Compare the security group rules before and after commandline restore",
                    tvaultconf.FAIL,
                )
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Compare the security group rules before and after commandline restore",
                    tvaultconf.PASS,
                )

            self._rules_verification_post_restore(security_group_names, data_sec_group_and_rules, rules_count)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()
            if len(restored_secgroup_ids) != 0:
                for secgrp in restored_secgroup_ids:
                    LOG.debug("Deleting security groups: {}".format(secgrp))
                    self.delete_security_group(secgrp)