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
                vm_cleanup=True,
            )
            LOG.debug("VM ID : " + str(vm_id))
            vms.append(vm_id)
        return vms

    def attach_empty_volume(self, vms):
        for vm in vms:
            volume_id = self.create_volume(volume_cleanup=True)
            LOG.debug("Volume ID: " + str(volume_id))
            self.attach_volume(volume_id, vm, attach_cleanup=True)
            LOG.debug("Volume attached")
        return vms

    def create_workload(self, vms):
        LOG.debug("\nvms : {}\n".format(vms))
        workload_id = self.workload_create(
            instances=vms,
            workload_name="for_remote_secgrp",
            workload_cleanup=True,
        )
        LOG.debug("Workload ID: " + str(workload_id))
        if workload_id is not None:
            self.wait_for_workload_tobe_available(workload_id)
            if self.getWorkloadStatus(workload_id) == "available":
                reporting.add_test_step("Create workload", tvaultconf.PASS)
            else:
                reporting.add_test_step("Create workload", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
        else:
            raise Exception("Workload creation failed")
        return workload_id

    # Generate security groups and rules data
    def generate_data_for_secgrp(self, security_group_count, rules_count):
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

    """ Method to create Security groups P, Q, R with distinct rules and assign the relationship like P -> Q -> R """

    def create_sec_groups_rule(self, secgrp_names, secgrp_list):
        LOG.debug("Create security group and rule")
        sec_groups = []
        for each in range(1, len(secgrp_list) + 1):
            sgid = self.create_security_group(
                name=secgrp_names + format(each),
                description="security group containing remote security group",
                secgrp_cleanup=True,
            )
            sec_groups.append(sgid)
            # Delete default security group rules
            self.delete_default_rules(sgid)
        for t in range(0, len(sec_groups) - 1):
            LOG.debug(
                "Creating rule with other details and remote group id in fashion P -> Q -> R "
            )
            secgrp = sec_groups[t]
            remote_secgrp = sec_groups[t + 1]
            remote_sec_flag = True
            # These security group will have atleast one remote sg/cyclic sg
            for each in secgrp_list[t]:
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
        # To create inherited sg, last security group will not have remote sg
        for each in secgrp_list[-1]:
            self.add_security_group_rule(
                parent_grp_id=sec_groups[-1],
                ip_proto=each["protocol"],
                from_prt=each["port_range_min"],
                to_prt=each["port_range_max"],
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
        reporting.add_test_script(str(__name__))

    @decorators.idempotent_id("c7aea6be-6c29-4d3b-bde9-98d515256c9d")
    @decorators.attr(type="workloadmgr_api")
    def test_wlm_cli(self):
        restored_sgids = []
        try:
            ### Verification of remote security group having inherited security groups ###
            LOG.debug("\nStarted test execution: ")
            secgrp_names = "test_secgroup-instance_wlm_cli"  + str(random.randint(0, 10000))
            security_group_count = 3
            rules_count = 2

            # 1. Create Security groups P, Q, R with distinct rules and assign the relationship like P -> Q -> R
            LOG.debug(
                "\nCreate Security groups P, Q, R with distinct rules and assign the relationship like P -> Q -> R "
            )
            secgrp_list = self.generate_data_for_secgrp(
                security_group_count, rules_count
            )
            sec_groups = self.create_sec_groups_rule(secgrp_names, secgrp_list)

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
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                LOG.debug("Full snapshot available!!")
            else:
                raise Exception("Create full snapshot failed")
            LOG.debug("\nFull snapshot ids : {}\n".format(snapshot_id))

            # Get the sec groups and rules list for verification post restore
            secgroups_before = self.list_security_groups()
            rules_before = self.list_security_group_rules()

            # 5. Delete vms, volumes, security groups
            LOG.debug("Delete VM + volume + security groups (P, Q, R)")
            self.delete_vm_secgroups(vms, sec_groups)
            time.sleep(60)

            # 6. Perform security groups restore through wlm command
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

            # 7. DB verification of the command execution
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
                    LOG.debug("Security group restore successfully completed")
                    reporting.add_test_step(
                        "Security group restore verification with DB completed successfully ",
                        tvaultconf.PASS,
                    )
                    self.created = True
                    break
                else:
                    if str(wc) == "error":
                        reporting.add_test_step(
                            "security group restore command execution has thrown error ",
                            tvaultconf.FAIL,
                        )
                        raise Exception("security group restore command verification has failed")

            # 8. Compare the security groups and rules before and after restore
            LOG.debug("Compare the security groups before and after restore")
            secgroups_after = self.list_security_groups()
            if len(secgroups_after) == len(secgroups_before):
                LOG.debug("Security group verification successful pre and post restore")
                reporting.add_test_step(
                    "Security group verification successful pre and post restore",
                    tvaultconf.PASS,
                )
            else:
                LOG.error("Security groups verification failed pre and post restore")
                reporting.add_test_step(
                    "Security groups verification failed pre and post restore",
                    tvaultconf.FAIL,
                )
                reporting.set_test_script_status(tvaultconf.FAIL)

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
                LOG.error(
                    "Security group rules verification failed pre and post restore"
                )
                reporting.add_test_step(
                    "Security group rules verification failed pre and post restore",
                    tvaultconf.FAIL,
                )
                reporting.set_test_script_status(tvaultconf.FAIL)

            # 9. Compare the security group & rules for restored security groups
            LOG.debug("Comparing restored security group & rules.")
            for t in range(0, len(sec_groups)):
                restored_secgrp = secgrp_names + str(t + 1)
                LOG.debug(
                    "Print name of restored security groups : {}".format(
                        restored_secgrp
                    )
                )

                sgid = self.get_security_group_id_by_name(restored_secgrp)
                # restored security groups to be cleaned after the execution
                restored_sgids.append(sgid)

                ### Verify security group rules for restored security groups ###
                LOG.debug(
                    "Verify security group rules for restored security group {}".format(
                        restored_secgrp
                    )
                )
                rule_list = self.list_secgroup_rules_for_secgroupid(sgid)
                LOG.debug(
                    "Retrieved rules list from security group: {}\n".format(
                        restored_secgrp
                    )
                )
                count = 0

                for each in secgrp_list[t]:
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
                    LOG.debug(
                        "Security group rules verification successful for restored secgroup {}".format(
                            restored_secgrp
                        )
                    )
                    reporting.add_test_step(
                        "Security group rules verification successful for restored secgroup {}".format(
                            restored_secgrp
                        ),
                        tvaultconf.PASS,
                    )
                else:
                    LOG.error(
                        "Security group rules verification failed for restored secgroup {}".format(
                            restored_secgrp
                        )
                    )
                    reporting.add_test_step(
                        "Security group rules verification failed for restored secgroup {}".format(
                            restored_secgrp
                        ),
                        tvaultconf.FAIL,
                    )
                    reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()
            if len(restored_sgids) != 0:
                for secgrp in restored_sgids:
                    LOG.debug("Deleting security groups: {}".format(secgrp))
                    self.delete_security_group(secgrp)
