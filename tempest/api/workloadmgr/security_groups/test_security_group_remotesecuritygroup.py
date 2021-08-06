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

    def create_vms_with_secgroup(self, sec_group, vm_count=1):
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
                vm_cleanup=False,
            )
            LOG.debug("VM ID : " + str(vm_id))
            vms.append(vm_id)
        return vms

    def attach_empty_volume(self, vms):
        for vm in vms:
            volume_id = self.create_volume(volume_cleanup=True)
            LOG.debug("Volume ID: " + str(volume_id))
            self.attach_volume(volume_id, vm, attach_cleanup=False)
            LOG.debug("Volume attached")
        return vms

    def create_workload(self, vms):
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
                    "Create workload-{}".format(workload_id), tvaultconf.PASS
                )
            else:
                reporting.add_test_step(
                    "Create workload-{}".format(workload_id), tvaultconf.FAIL
                )
                reporting.set_test_script_status(tvaultconf.FAIL)
        else:
            reporting.add_test_step(
                "Create workload-{}".format(workload_id), tvaultconf.FAIL
            )
            reporting.set_test_script_status(tvaultconf.FAIL)
            raise Exception("Workload creation failed")
        return workload_id

    """ Method to create Security groups P, Q, R with distinct rules and assign the relationship like P -> Q -> R -> P """

    def create_sec_groups_rule(self, secgrp_count, secgrp_name, rule_values):
        LOG.debug("Create security group and rule for {}".format(secgrp_name))
        sec_groups = []
        for each in range(1, secgrp_count + 1):
            sgid = self.create_security_group(
                name=secgrp_name + format(each),
                description="security group containing remote security group",
                secgrp_cleanup=True,
            )
            sec_groups.append(sgid)
        for each in range(0, len(rule_values)):
            LOG.debug(
                "Creating rule with other details and remote group id in fashion P -> Q -> R -> P"
            )
            self.add_security_group_rule(
                parent_grp_id=sec_groups[each],
                remote_grp_id=sec_groups[each - 1],
                ip_proto=rule_values[each]["protocol"],
                from_prt=rule_values[each]["port_range_min"],
                to_prt=rule_values[each]["port_range_max"],
            )
            # Creating more rules
            self.add_security_group_rule(
                parent_grp_id=sec_groups[each],
                ip_proto=rule_values[each]["protocol"],
                from_prt=rule_values[each]["port_range_min"],
                to_prt=rule_values[each]["port_range_max"],
            )
        LOG.debug(
            "Security groups collection: {} and last entry {}".format(
                sec_groups, sec_groups[-1]
            )
        )
        return sec_groups

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    @decorators.idempotent_id("59fd74ab-0b0f-474a-8c53-324babf5eb1c")
    @decorators.attr(type="workloadmgr_api")
    def test_security_group_remotesecuritygroup(self):
        try:
            ### Verification of remote security group post restore ###
            LOG.debug("\nStarted test execution: ")
            reporting.add_test_script(
                "tempest.api.workloadmgr.security_groups.test_security_group_remotesecuritygroup"
            )
            status = 1
            deleted = 0
            secgrp_names_list = [
                "test_secgroup-PQR",
                "test_secgroup-ABC",
                "test_secgroup-XYZ",
            ]
            secgrp_count = 3
            # Create security group with cyclic SG rules, 2 additional rules (Ingress and Egress) and 2 default rules
            ip_protocols = ["tcp", "udp"]
            same_rule = []
            for i in range(0, secgrp_count):
                protocol = random.choice(ip_protocols)
                from_port = random.randrange(1500, 2700)
                to_port = random.randrange(2800, 3999)
                values = {
                    "protocol": protocol,
                    "port_range_min": from_port,
                    "port_range_max": to_port,
                }
                same_rule.append(values)
            LOG.debug("rule details to be added: {}".format(same_rule))

            diff_rule = []
            for i in range(0, secgrp_count):
                protocol = random.choice(ip_protocols)
                from_port = random.randrange(4000, 5000)
                to_port = random.randrange(5000, 6000)
                values = {
                    "protocol": protocol,
                    "port_range_min": from_port,
                    "port_range_max": to_port,
                }
                diff_rule.append(values)
            LOG.debug("rule details to be added: {}".format(diff_rule))

            # 1. Create Security groups P, Q, R with distinct rules and assign the relationship like P -> Q -> R -> P
            LOG.debug(
                "\nCreate Security groups P, Q, R with distinct rules and assign the relationship like P -> Q -> R -> P"
            )
            sec_groups = self.create_sec_groups_rule(
                secgrp_count, secgrp_names_list[0], same_rule
            )

            # 2. Create an image booted instance with Security group P and attach an empty volume.
            LOG.debug(
                "Create an image booted instance with Security group P and attach an empty volume."
            )
            vms = self.create_vms_with_secgroup(sec_groups[0])
            LOG.debug("\nVMs : {}\n".format(vms))
            vms = self.attach_empty_volume(vms)
            LOG.debug("\nEmpty Volume attached : {}\n".format(vms))

            # 3. Create a workload for the instance.
            LOG.debug("Create a workload for this instance.")
            workload_id = self.create_workload(vms)
            LOG.debug("\nWorkload created : {}\n".format(workload_id))

            # 4. Take a Full snapshot
            LOG.debug("Take a full snapshot")
            snapshot_id = self.workload_snapshot(
                workload_id, True, snapshot_cleanup=True
            )
            time.sleep(5)
            self.wait_for_workload_tobe_available(workload_id)
            if self.getSnapshotStatus(workload_id, snapshot_id) == "available":
                reporting.add_test_step(
                    "Create full snapshot-{}".format(snapshot_id), tvaultconf.PASS
                )
                LOG.debug("Full snapshot available!!")
            else:
                reporting.add_test_step(
                    "Create full snapshot-{}".format(snapshot_id), tvaultconf.FAIL
                )
                raise Exception("Snapshot creation failed")
            LOG.debug("\nFull snapshot ids : {}\n".format(snapshot_id))

            # 5. Delete vms, volumes, security groups
            self.delete_vm_secgroups(vms, sec_groups)
            time.sleep(60)
            deleted = 1

            # 6. Create security groups A, B, C with different rules other than P, Q, R and assign relationship A -> B -> C -> A
            LOG.debug(
                "Create security groups A, B, C with different rules other than P, Q, R and assign relationship A -> B -> C -> A"
            )
            self.create_sec_groups_rule(secgrp_count, secgrp_names_list[1], diff_rule)

            # 7. Create security groups X, Y, Z with same rules as that of P, Q, R and assign relationship X -> Y -> Z -> X
            LOG.debug(
                "Create security groups X, Y, Z with same rules as that of P, Q, R and assign relationship X -> Y -> Z -> X"
            )
            sg_samerules = self.create_sec_groups_rule(
                secgrp_count, secgrp_names_list[2], same_rule
            )
            secgroups_before = self.list_security_groups()
            rules_before = self.list_security_group_rules()

            ### 8. Perform one click restore ###
            LOG.debug("Perform one click restore")
            restore_id = self.snapshot_restore(
                workload_id, snapshot_id, restore_cleanup=True
            )

            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            if (
                self.getRestoreStatus(workload_id, snapshot_id, restore_id)
                == "available"
            ):
                reporting.add_test_step(
                    "Oneclick-{}".format(snapshot_id), tvaultconf.PASS
                )
                LOG.debug("Oneclick restore passed")
            else:
                reporting.add_test_step(
                    "Oneclick restore-{}".format(snapshot_id), tvaultconf.FAIL
                )
                LOG.debug("Oneclick restore failed")
                raise Exception("Oneclick restore failed")

            restored_vms = self.get_restored_vm_list(restore_id)
            LOG.debug("\nRestored vms : {}\n".format(restored_vms))

            # 9. Compare the security groups and rules before and after restore
            LOG.debug("Compare the security groups before and after restore")
            secgroups_after = self.list_security_groups()
            if secgroups_after == secgroups_before:
                LOG.debug("Security group verification successful pre and post restore")
                reporting.add_test_step(
                    "Security group verification successful pre and post restore",
                    tvaultconf.PASS,
                )
            else:
                LOG.error("Security groups verification failed ")
                reporting.add_test_step(
                    "Security groups verification failed ",
                    tvaultconf.FAIL,
                )
                status = 0

            LOG.debug("Compare the security group rules before and after restore")
            rules_after = self.list_security_group_rules()
            if rules_after == rules_before:
                LOG.debug(
                    "Security group rules verification successful pre and post restore"
                )
                reporting.add_test_step(
                    "Security group rules verification successful pre and post restore",
                    tvaultconf.PASS,
                )
            else:
                LOG.error("Security group rules verification failed ")
                reporting.add_test_step(
                    "Security group rules verification failed ",
                    tvaultconf.FAIL,
                )
                status = 0

            # 10. Compare the security group & rules assigned to the restored instance
            restored_secgrps = self.getRestoredSecGroupPolicies(restored_vms)
            if restored_secgrps == None:
                reporting.add_test_step(
                    "Security group is not attached to restored vm {}".format(
                        restored_vms
                    ),
                    tvaultconf.FAIL,
                )
                status = 0
                raise Exception("Security group is not attached to restored vm")
            else:
                LOG.debug(
                    "Security group is attached to restored vm {}".format(restored_vms)
                )
                reporting.add_test_step(
                    "Security group is attached to restored vm {}".format(restored_vms),
                    tvaultconf.PASS,
                )

                LOG.debug(
                    "Comparing security group & rules assigned to the restored instances."
                )
                for restored_secgrp in restored_secgrps:
                    LOG.debug(
                        "Print names of restored security groups : {}".format(
                            restored_secgrp["name"]
                        )
                    )

                    if self.verifySecurityGroupsByname(restored_secgrp["name"]):
                        LOG.debug(
                            "Security group verification successful for restored vm {}".format(
                                restored_secgrp["name"]
                            )
                        )
                        reporting.add_test_step(
                            "Security group verification successful for restored vm {}".format(
                                restored_secgrp["name"]
                            ),
                            tvaultconf.PASS,
                        )
                    else:
                        LOG.error(
                            "Security group verification failed for restored vm {}".format(
                                restored_secgrp["name"]
                            )
                        )
                        reporting.add_test_step(
                            "Security group verification failed for restored vm {}".format(
                                restored_secgrp["name"]
                            ),
                            tvaultconf.FAIL,
                        )
                        status = 0

                # Compare rules for restored/instance attached security groups
                for each in range(0, len(sg_samerules)):
                    LOG.debug(
                        "Verify security group rules for restored security group {}".format(
                            sg_samerules[each]
                        )
                    )
                    rule_list = self.list_secgroup_rules_for_secgroupid(
                        sg_samerules[each]
                    )
                    LOG.debug(
                        "Retrieved rules list from security group: {}\n".format(
                            sg_samerules[each]
                        )
                    )
                    result = False
                    for rule in rule_list:
                        result = self.verifySecurityGroupRules(
                            rule["id"], sg_samerules[each], same_rule[each]
                        )

                    if result == True:
                        LOG.debug(
                            "Security group verification successful for restored vm for secgroup {}".format(
                                sg_samerules[each]
                            )
                        )
                        reporting.add_test_step(
                            "Security group verification successful for restored vm for secgroup {}".format(
                                sg_samerules[each]
                            ),
                            tvaultconf.PASS,
                        )
                    else:
                        LOG.error(
                            "Security group verification failed for restored vm for secgroup {}".format(
                                sg_samerules[each]
                            )
                        )
                        reporting.add_test_step(
                            "Security group verification failed for restored vm for secgroup {}".format(
                                sg_samerules[each]
                            ),
                            tvaultconf.FAIL,
                        )
                        status = 0

        except Exception as e:
            LOG.error("Exception: " + str(e))
            if deleted == 0:
                try:
                    self.delete_vms([*vms])
                except BaseException:
                    pass

        finally:
            if status != 1:
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.set_test_script_status(tvaultconf.PASS)
            reporting.test_case_to_write()

    @decorators.idempotent_id("44cc9afa-d8ee-4b14-a319-20784ef2ef00")
    @decorators.attr(type="workloadmgr_api")
    def test_security_group_remotesg_cyclic_diffrule(self):
        try:
            ### Verification of remote security group post restore ###
            LOG.debug("\nStarted test execution: ")
            reporting.add_test_script(
                "tempest.api.workloadmgr.security_groups.test_security_group_remotesg_cyclic_diffrule"
            )
            status = 1
            deleted = 0
            secgrp_names = "test_secgroup_instance_restore"
            secgrp_count = 3

            ip_protocols = ["tcp", "udp"]
            instance_attached_rules = []

            for i in range(0, secgrp_count):
                protocol = random.choice(ip_protocols)
                from_port = random.randrange(2000, 2999)
                to_port = random.randrange(3000, 3999)
                values = {
                    "protocol": protocol,
                    "port_range_min": from_port,
                    "port_range_max": to_port,
                }
                instance_attached_rules.append(values)
            LOG.debug("rule details to be added: {}".format(instance_attached_rules))

            # 1. Create Security groups P, Q, R with distinct rules and assign the relationship like P -> Q -> R -> P
            LOG.debug(
                "\nCreate Security groups P, Q, R with distinct rules and assign the relationship like P -> Q -> R -> P"
            )
            sec_groups = self.create_sec_groups_rule(
                secgrp_count, secgrp_names, instance_attached_rules
            )

            # 2. Create an image booted instance with Security group P and attach an empty volume.
            LOG.debug(
                "Create an image booted instance with Security group P and attach an empty volume."
            )
            vms = self.create_vms_with_secgroup(sec_groups[0])
            LOG.debug("\nVMs : {}\n".format(vms))
            vms = self.attach_empty_volume(vms)
            LOG.debug("\nEmpty Volume attached : {}\n".format(vms))

            # 3. Create a workload for the instance.
            LOG.debug("Create a workload for this instance.")
            workload_id = self.create_workload(vms)
            LOG.debug("\nWorkload created : {}\n".format(workload_id))

            # 4. Take a Full snapshot
            LOG.debug("Take a full snapshot")
            snapshot_id = self.workload_snapshot(
                workload_id, True, snapshot_cleanup=True
            )
            time.sleep(5)
            self.wait_for_workload_tobe_available(workload_id)
            if self.getSnapshotStatus(workload_id, snapshot_id) == "available":
                reporting.add_test_step(
                    "Create full snapshot-{}".format(snapshot_id), tvaultconf.PASS
                )
                LOG.debug("Full snapshot available!!")
            else:
                reporting.add_test_step(
                    "Create full snapshot-{}".format(snapshot_id), tvaultconf.FAIL
                )
                raise Exception("Snapshot creation failed")
            LOG.debug("\nFull snapshot ids : {}\n".format(snapshot_id))

            secgroups_before = self.list_security_groups()
            rules_before = self.list_security_group_rules()

            # 5. Delete vms, volumes, security groups
            LOG.debug("Delete VM + volume + security groups (P, Q, R)")
            self.delete_vm_secgroups(vms, sec_groups)
            time.sleep(60)
            deleted = 1

            ### 8. Perform one click restore ###
            LOG.debug("Perform one click restore")
            restore_id = self.snapshot_restore(
                workload_id, snapshot_id, restore_cleanup=True
            )

            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            if (
                self.getRestoreStatus(workload_id, snapshot_id, restore_id)
                == "available"
            ):
                reporting.add_test_step(
                    "Oneclick-{}".format(snapshot_id), tvaultconf.PASS
                )
                LOG.debug("Oneclick restore passed")
            else:
                reporting.add_test_step(
                    "Oneclick restore-{}".format(snapshot_id), tvaultconf.FAIL
                )
                LOG.debug("Oneclick restore failed")
                raise Exception("Oneclick restore failed")

            restored_vms = self.get_restored_vm_list(restore_id)
            LOG.debug("\nRestored vms : {}\n".format(restored_vms))

            # 9. Compare the security groups and rules before and after restore
            LOG.debug("Compare the security groups before and after restore")
            secgroups_after = self.list_security_groups()
            if len(secgroups_after) == len(secgroups_before):
                LOG.debug("Security group verification successful pre and post restore")
                reporting.add_test_step(
                    "Security group verification successful pre and post restore",
                    tvaultconf.PASS,
                )
            else:
                LOG.error("Security groups verification failed ")
                reporting.add_test_step(
                    "Security groups verification failed ",
                    tvaultconf.FAIL,
                )
                status = 0

            LOG.debug("Compare the security group rules before and after restore")
            rules_after = self.list_security_group_rules()
            if len(rules_after) == len(rules_before):
                LOG.debug(
                    "Security group rules verification successful pre and post restore"
                )
                reporting.add_test_step(
                    "Security group rules verification successful pre and post restore",
                    tvaultconf.PASS,
                )
            else:
                LOG.error("Security group rules verification failed ")
                reporting.add_test_step(
                    "Security group rules verification failed ",
                    tvaultconf.FAIL,
                )
                status = 0

            # 10. Compare the security group & rules assigned to the restored instance
            restored_secgrps = self.getRestoredSecGroupPolicies(restored_vms)
            LOG.debug(
                "Comparing security group & rules assigned to the restored instances."
            )

            for restored_secgrp in restored_secgrps:
                LOG.debug(
                    "Print names of restored security groups : {}".format(
                        restored_secgrp["name"]
                    )
                )

                if self.verifySecurityGroupsByname(restored_secgrp["name"]):
                    LOG.debug(
                        "Security group verification successful for restored vm {}".format(
                            restored_secgrp["name"]
                        )
                    )
                    reporting.add_test_step(
                        "Security group verification successful for restored vm {}".format(
                            restored_secgrp["name"]
                        ),
                        tvaultconf.PASS,
                    )
                else:
                    LOG.error(
                        "Security group verification failed for restored vm {}".format(
                            restored_secgrp["name"]
                        )
                    )
                    reporting.add_test_step(
                        "Security group verification failed for restored vm {}".format(
                            restored_secgrp["name"]
                        ),
                        tvaultconf.FAIL,
                    )
                    status = 0

            # Compare rules for restored/instance attached security groups
            for each in range(0, len(sec_groups)):
                restored_secgrp = "snap_of_{}{}".format(secgrp_names, each + 1)
                LOG.debug(
                    "Verify security group rules for restored security group {}".format(
                        restored_secgrp
                    )
                )
                sgid = self.get_security_group_id_by_name(restored_secgrp)
                rule_list = self.list_secgroup_rules_for_secgroupid(sgid)
                LOG.debug(
                    "Retrieved rules list from security group: {}\n".format(
                        restored_secgrp
                    )
                )
                result = False
                for rule in rule_list:
                    result = self.verifySecurityGroupRules(
                        rule["id"], sgid, instance_attached_rules[each]
                    )

                if result == True:
                    LOG.debug(
                        "Security group rules verification successful for restored vm {}".format(
                            restored_secgrp
                        )
                    )
                    reporting.add_test_step(
                        "Security group rules verification successful for restored vm {}".format(
                            restored_secgrp
                        ),
                        tvaultconf.PASS,
                    )
                else:
                    LOG.error(
                        "Security group rules verification failed for restored vm {}".format(
                            restored_secgrp
                        )
                    )
                    reporting.add_test_step(
                        "Security group rules verification failed for restored vm {}".format(
                            restored_secgrp
                        ),
                        tvaultconf.FAIL,
                    )
                    status = 0

        except Exception as e:
            LOG.error("Exception: " + str(e))
            if deleted == 0:
                try:
                    self.delete_vms([*vms])
                except BaseException:
                    pass

        finally:
            if status != 1:
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.set_test_script_status(tvaultconf.PASS)
            reporting.test_case_to_write()
