import logging
import os
import random
import sys
import time

from oslo_log import log as logging

from tempest import command_argument_string
from tempest import config
from tempest import reporting
from tempest import test
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

    # Delete default security group rules
    def delete_default_rules(self, secgrp_id):
        LOG.debug("Delete default rules from given security group")
        rule_list = self.list_secgroup_rules_for_secgroupid(secgrp_id)
        for each in rule_list:
            self.security_group_rules_client.delete_security_group_rule(each["id"])

    """ Method to create Security groups P, Q, R with distinct rules and assign the relationship like P -> Q -> R -> P """

    def create_sec_groups_rule(self, count, secgrp_name, diff_rule=False):
        LOG.debug("Create security group and rule for {}".format(secgrp_name))
        sec_groups = []
        ip_protocol = "TCP"
        from_port = 2000
        to_port = 2100
        for each in range(1, count + 1):
            sgid = self.create_security_group(
                name=secgrp_name + format(each),
                description="security group containing remote security group",
                secgrp_cleanup=True,
            )
            sec_groups.append(sgid)
            # Delete default security group rules
            self.delete_default_rules(sgid)
        for each in range(0, count):
            LOG.debug(
                "Creating rule with other details and remote group id in fashion P -> Q -> R -> P"
            )
            if diff_rule == True:
                ip_protocol = "UDP"
                from_port = random.randrange(4000, 5000)
                to_port = random.randrange(5000, 6000)
            self.add_security_group_rule(
                parent_grp_id=sec_groups[each],
                remote_grp_id=sec_groups[each - 1],
                ip_proto=ip_protocol,
                from_prt=from_port,
                to_prt=to_port,
            )
        LOG.debug(
            "Security groups collection: {} and last entry {}".format(
                sec_groups, sec_groups[-1]
            )
        )
        return sec_groups

    # Compare the security groups by name and assert if verification fails
    def assertCompareSecurityGroupSuccessful(self, no_of_secgrp, secgrp_name):
        LOG.debug("Compare security groups")
        sec_groups = []
        body = self.security_groups_client.list_security_groups()
        security_groups = body["security_groups"]
        count = 0
        LOG.debug(secgrp_name, no_of_secgrp)
        for n in security_groups:
            if secgrp_name in n["name"]:
                count += 1
                sec_groups.append(n["id"])
        msg = "Security-group list doesn't contain security-group with name {}".format(
            secgrp_name
        )
        self.assertNotEmpty(security_groups, msg)
        self.assertEqual(no_of_secgrp, count, msg)

    # Compare the security group & rules assigned to the restored instance and assert if verification fails
    def assertCompareSecurityGroupRulesSuccesful(
        self, count, secgrp_name, diff_rule=False
    ):
        LOG.debug("Compare security group rules")
        expected = {
            "protocol": "tcp",
            "port_range_min": 2000,
            "port_range_max": 2100,
        }
        for i in range(1, count + 1):
            str_secgrp = secgrp_name + format(i)
            secgrp_id = self.get_security_group_id_by_name(str_secgrp)
            rule_list = self.list_secgroup_rules_for_secgroupid(secgrp_id)
            for each in rule_list:
                self.assertEqual(
                    2,
                    len(rule_list),
                    "Count of rules does not match: Expected %d and Actual %d"
                    % (2, len(rule_list)),
                )
                if diff_rule == False:
                    for key, value in expected.items():
                        self.assertEqual(
                            value,
                            each[key],
                            "Field %s of the created security group "
                            "rule does not match with %s." % (key, value),
                        )
                else:
                    for key, value in expected.items():
                        self.assertNotEqual(
                            value,
                            each[key],
                            "Field %s of the created security group "
                            "rules are not different %s." % (key, value),
                        )
                self.assertNotEmpty(
                    each["remote_group_id"],
                    "remote group id is not restored for rule: {}".format(each["id"]),
                )
                self.assertNotEqual(
                    each["remote_group_id"],
                    secgrp_id,
                    "remote group id from different security group is not present",
                )

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
            status = 0
            deleted = 0
            secgrp_names_list = [
                "test_secgroup-PQR",
                "test_secgroup-ABC",
                "test_secgroup-XYZ",
            ]
            secgrp_count = len(secgrp_names_list)

            # 1. Create Security groups P, Q, R with distinct rules and assign the relationship like P -> Q -> R -> P
            LOG.debug(
                "\nCreate Security groups P, Q, R with distinct rules and assign the relationship like P -> Q -> R -> P"
            )
            sec_groups = self.create_sec_groups_rule(secgrp_count, secgrp_names_list[0])

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
            LOG.debug("Delete VM + volume + security groups (P, Q, R)")
            self.delete_vms([*vms])
            time.sleep(60)
            deleted = 1

            # 6. Create security groups A, B, C with different rules other than P, Q, R and assign relationship A -> B -> C -> A
            LOG.debug(
                "Create security groups A, B, C with different rules other than P, Q, R and assign relationship A -> B -> C -> A"
            )
            self.create_sec_groups_rule(secgrp_count, secgrp_names_list[2], True)

            # 7. Create security groups X, Y, Z with same rules as that of P, Q, R and assign relationship X -> Y -> Z -> X
            LOG.debug(
                "Create security groups X, Y, Z with same rules as that of P, Q, R and assign relationship X -> Y -> Z -> X"
            )
            self.create_sec_groups_rule(secgrp_count, secgrp_names_list[1])

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

            restore_secgrp_name = []
            for vm in restored_vms:
                vmdetails = self.get_vm_details(vm)
                LOG.debug("\nRestored VM details: {}".format(vmdetails))
                server_vm = vmdetails["server"]
                LOG.debug(
                    "\nRestored VM details - server : {}".format(vmdetails["server"])
                )
                # for each in server_vm:
                restore_secgrp_name = server_vm["security_groups"]
                LOG.debug(
                    "List of restored security group policies: {}".format(
                        restore_secgrp_name
                    )
                )

            # 9. Compare the security group & rules assigned to the restored instance
            LOG.debug(
                "Comparing security group & rules assigned to the restored instances."
            )

            for vm_restore_secgrp_name in restore_secgrp_name:
                LOG.debug(
                    "Print names of security groups: {}".format(
                        vm_restore_secgrp_name["name"]
                    )
                )
                if self.assertCompareSecurityGroupSuccessful(
                    secgrp_count, vm_restore_secgrp_name["name"]
                ):
                    # if (self.assertCompareSecurityGroupSuccessful(secgrp_count, str_secgrp)):
                    reporting.add_test_step(
                        "Security group verification successful for restored vm {}".format(
                            vm_restore_secgrp_name
                        ),
                        tvaultconf.PASS,
                    )
                else:
                    reporting.add_test_step(
                        "Security group verification failed for restored vm {}".format(
                            vm_restore_secgrp_name
                        ),
                        tvaultconf.FAIL,
                    )

                if self.assertCompareSecurityGroupRulesSuccesful(
                    secgrp_count, vm_restore_secgrp_name["name"], False
                ):
                    reporting.add_test_step(
                        "Security group rules verification successful for newly created rules post restore having different rules {}".format(
                            vm_restore_secgrp_name
                        ),
                        tvaultconf.PASS,
                    )
                    status = 1
                else:
                    reporting.add_test_step(
                        "Security group rules verification failed for newly created rules post restore having different rules {}".format(
                            vm_restore_secgrp_name
                        ),
                        tvaultconf.FAIL,
                    )

            # 10. Compare the security groups and rules before and after restore
            LOG.debug("Compare the security groups before and after restore")
            for each in secgrp_names_list:
                # Changes for verification for different rule
                LOG.debug("Verify for different rule")
                if each == secgrp_names_list[2]:
                    diff_rule = True
                else:
                    diff_rule = False

                # Changes for verification of all restored secgroups named with 'snap_of_'
                LOG.debug("Verify for restored secgroup {}".format(each))
                if each == secgrp_names_list[0]:
                    # each = secgrp_names_list[0]
                    each = "snap_of_{}".format(secgrp_names_list[0])
                    LOG.debug("Verify for restored secgroup {}".format(each))

                # Verification for security groups and rules
                if self.assertCompareSecurityGroupSuccessful(secgrp_count, each):
                    reporting.add_test_step(
                        "Security group verification successful for newly created group {}".format(
                            each
                        ),
                        tvaultconf.PASS,
                    )
                else:
                    reporting.add_test_step(
                        "Security group verification failed for newly created group post restore {}".format(
                            secgrp_names_list[1]
                        ),
                        tvaultconf.FAIL,
                    )

                if self.assertCompareSecurityGroupRulesSuccesful(
                    secgrp_count, each, diff_rule
                ):
                    reporting.add_test_step(
                        "Security group rules verification successful for newly created rules post restore {}".format(
                            each
                        ),
                        tvaultconf.PASS,
                    )
                else:
                    reporting.add_test_step(
                        "Security group rules verification failed for newly created rules post restore {}".format(
                            each
                        ),
                        tvaultconf.FAIL,
                    )

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            if deleted == 0:
                try:
                    self.delete_vms([*vms])
                except BaseException:
                    pass
            if status != 1:
                reporting.set_test_script_status(tvaultconf.FAIL)
                reporting.test_case_to_write()
