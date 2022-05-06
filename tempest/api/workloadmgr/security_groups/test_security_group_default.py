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
    restored_secgroup_ids = []

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()
        reporting.add_test_script(str(__name__))

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
                    "Create workload", tvaultconf.PASS
                )
        else:
            reporting.add_test_step(
                "Create workload", tvaultconf.FAIL
            )
            reporting.set_test_script_status(tvaultconf.FAIL)
            raise Exception("Workload creation failed")
        return workload_id

    def _take_full_snapshot(self, workload_id):
        snapshot_id = self.workload_snapshot(workload_id, True, snapshot_cleanup=True)
        time.sleep(5)
        self.wait_for_workload_tobe_available(workload_id)
        if self.getSnapshotStatus(workload_id, snapshot_id) == "available":
            reporting.add_test_step(
                "Create full snapshot", tvaultconf.PASS
            )
            LOG.debug("Full snapshot available!!")
        else:
            reporting.add_test_step(
                "Create full snapshot", tvaultconf.FAIL
            )
            reporting.set_test_script_status(tvaultconf.FAIL)
            raise Exception("Snapshot creation failed")
        LOG.debug("\nFull snapshot ids : {}\n".format(snapshot_id))
        return snapshot_id

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

    def _create_sec_groups_rule(self, security_group_names, data_sec_group_and_rules):
        LOG.debug("Create security group and rule")
        created_security_groups = []
        for each in range(1, len(data_sec_group_and_rules) + 1):
            sgid = self.create_security_group(
                name=security_group_names + format(each),
                description="security group with distinct rules",
                secgrp_cleanup=True,
            )
            created_security_groups.append(sgid)
            # Delete default security group rules
            self.delete_default_rules(sgid)
        for t in range(0, len(created_security_groups)):
            LOG.debug(
                "Creating rule with other details "
            )
            secgrp = created_security_groups[t]
            for each in data_sec_group_and_rules[t]:
                self.add_security_group_rule(
                    parent_grp_id=secgrp,
                    ip_proto=each["protocol"],
                    from_prt=each["port_range_min"],
                    to_prt=each["port_range_max"],
                )
        return created_security_groups

    def _security_group_and_rules_verification(self, security_group_names, data_sec_group_and_rules, rules_count):
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

    # Test case automation for #OS-1892 : Security_Group_Restore_using_CLI_for_single_group
    # Test case automation for #OS-1893 : Security_Group_Restore_using_CLI_for_multiple_groups
    @decorators.attr(type="workloadmgr_cli")
    def test_01_security_group(self):
        test_var = "tempest.api.workloadmgr.security_group.test_"
        tests = [[test_var + "wlm_cli_single_security_group", 1, 3],
                 [test_var + "wlm_cli_multiple_security_groups", 5, 3]]

        for test in tests:
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
                    created_security_groups = self._create_sec_groups_rule(security_group_names, data_sec_group_and_rules)
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
                self._security_group_and_rules_verification(security_group_names, data_sec_group_and_rules, rules_count)

            except Exception as e:
                LOG.error("Exception: " + str(e))
                reporting.add_test_step(str(e), tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            finally:
                reporting.test_case_to_write()
                # Deleting restored security groups after verification
                if len(self.restored_secgroup_ids) != 0:
                    for secgrp in self.restored_secgroup_ids:
                        LOG.debug("Deleting security groups: {}".format(secgrp))
                        self.delete_security_group(secgrp)
