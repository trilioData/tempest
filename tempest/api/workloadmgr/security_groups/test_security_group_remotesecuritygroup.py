import os
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
                "test_secgroup-XYZ-new",
            ]
            secgrp_names_list_post_restore = [
                "test_secgroup-ABC",
                "test_secgroup-XYZ-new",
            ]
            secgrp_count = len(secgrp_names_list)
            # Create security group with cyclic SG rules, 2 additional rules (Ingress and Egress) and 2 default rules
            rules_count = 6

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
            vol = []
            for vm in vms:
                LOG.debug("Get list of all volumes to be deleted")
                vol.append(self.get_attached_volumes(vm))
            self.delete_vms([*vms])
            LOG.debug("Delete volumes: {}".format(vol))
            self.delete_volumes(vol)
            for secgrp in sec_groups:
                self.delete_security_group(secgrp)
                LOG.debug("Delete security groups: {}".format(secgrp))
            time.sleep(60)
            deleted = 1

            # 6. Create security groups A, B, C with different rules other than P, Q, R and assign relationship A -> B -> C -> A
            LOG.debug(
                "Create security groups A, B, C with different rules other than P, Q, R and assign relationship A -> B -> C -> A"
            )
            self.create_sec_groups_rule(secgrp_count, secgrp_names_list[1], True)

            # 7. Create security groups X, Y, Z with same rules as that of P, Q, R and assign relationship X -> Y -> Z -> X
            LOG.debug(
                "Create security groups X, Y, Z with same rules as that of P, Q, R and assign relationship X -> Y -> Z -> X"
            )
            self.create_sec_groups_rule(secgrp_count, secgrp_names_list[2])

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
            for each in secgrp_names_list_post_restore:
                # Changes for verification for different rule
                if each == secgrp_names_list_post_restore[0]:
                    LOG.debug("Verify for different rule")
                    diff_rule = True
                else:
                    diff_rule = False

                LOG.debug("Verify for security group list: {}".format(each))
                # Verification for security groups and rules
                if self.verifySecurityGroups(secgrp_count, each) == True:
                    LOG.debug(
                        "Security group verification successful for newly created group {}".format(
                            each
                        )
                    )
                    reporting.add_test_step(
                        "Security group verification successful for newly created group {}".format(
                            each
                        ),
                        tvaultconf.PASS,
                    )
                else:
                    LOG.debug(
                        "Security group verification failed for newly created group post restore {}".format(
                            each
                        )
                    )
                    reporting.add_test_step(
                        "Security group verification failed for newly created group post restore {}".format(
                            each
                        ),
                        tvaultconf.FAIL,
                    )
                    status = 0
                if (
                    self.verifySecurityGroupRules(
                        secgrp_count, rules_count, each, False, diff_rule
                    )
                    == True
                ):
                    LOG.debug(
                        "Security group rules verification successful for newly created rules post restore {}".format(
                            each
                        )
                    )
                    reporting.add_test_step(
                        "Security group rules verification successful for newly created rules post restore {}".format(
                            each
                        ),
                        tvaultconf.PASS,
                    )
                else:
                    LOG.debug(
                        "Security group rules verification failed for newly created rules post restore {}".format(
                            each
                        )
                    )
                    reporting.add_test_step(
                        "Security group rules verification failed for newly created rules post restore {}".format(
                            each
                        ),
                        tvaultconf.FAIL,
                    )
                    status = 0

            # 10. Compare the security group & rules assigned to the restored instance
            restore_secgrp_name = self.getRestoredSecGroupPolicies(restored_vms)
            LOG.debug(
                "Comparing security group & rules assigned to the restored instances."
            )

            for vm_restore_secgrp_name in restore_secgrp_name:
                LOG.debug(
                    "Print names of security groups: {}".format(
                        vm_restore_secgrp_name["name"]
                    )
                )
                if self.verifySecurityGroups(1, vm_restore_secgrp_name["name"]) == True:
                    LOG.debug(
                        "Security group verification successful for restored vm {}".format(
                            vm_restore_secgrp_name
                        )
                    )
                    reporting.add_test_step(
                        "Security group verification successful for restored vm {}".format(
                            vm_restore_secgrp_name
                        ),
                        tvaultconf.PASS,
                    )
                else:
                    LOG.debug(
                        "Security group verification failed for restored vm {}".format(
                            vm_restore_secgrp_name
                        )
                    )
                    reporting.add_test_step(
                        "Security group verification failed for restored vm {}".format(
                            vm_restore_secgrp_name
                        ),
                        tvaultconf.FAIL,
                    )
                    status = 0
                if (
                    self.verifySecurityGroupRules(
                        1, rules_count, vm_restore_secgrp_name["name"], True
                    )
                    == True
                ):
                    LOG.debug(
                        "Security group rules verification successful for restored vm {}".format(
                            vm_restore_secgrp_name
                        )
                    )
                    reporting.add_test_step(
                        "Security group rules verification successful for restored vm {}".format(
                            vm_restore_secgrp_name
                        ),
                        tvaultconf.PASS,
                    )
                else:
                    LOG.debug(
                        "Security group rules verification failed for restored vm {}".format(
                            vm_restore_secgrp_name
                        )
                    )
                    reporting.add_test_step(
                        "Security group rules verification failed for restored vm {}".format(
                            vm_restore_secgrp_name
                        ),
                        tvaultconf.FAIL,
                    )
                    status = 0

            if status != 1:
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.set_test_script_status(tvaultconf.PASS)
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
