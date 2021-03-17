import json
import os
import sys
import time

import yaml
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

    def assign_floating_ips(self, vm_id, cleanup):
        fip = self.get_floating_ips()
        LOG.debug("\nAvailable floating ips are {}: \n".format(fip))
        self.set_floating_ip(str(fip[0]), vm_id, floatingip_cleanup=cleanup)
        return(fip[0])

    def data_ops(self, flo_ip, data_dir_path, file_count):
        ssh = self.SshRemoteMachineConnectionWithRSAKey(str(flo_ip))
        stdin, stdout, stderr = ssh.exec_command(
            "sudo apt install qemu-guest-agent")
        self.addCustomfilesOnLinuxVM(ssh, data_dir_path, file_count)
        ssh.close()

    def calcmd5sum(self, flip, data_dir_path):
        mdb = {}
        ssh = self.SshRemoteMachineConnectionWithRSAKey(str(flip))
        mdb[str(flip)] = self.calculatemmd5checksum(ssh, data_dir_path)
        ssh.close()
        return mdb

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
        return(snapshot_id)

    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    @decorators.attr(type='workloadmgr_cli')
    def test_1_image_booted(self):
        try:
            deleted = 0
            ## VM and Workload ###
            tests = [['tempest.api.workloadmgr.restore.test_image_booted_Selective-restore',
                      0],
                     ['tempest.api.workloadmgr.restore.test_image_booted_Inplace-restore',
                      0],
                     ['tempest.api.workloadmgr.restore.test_image_booted_Oneclick-restore',
                      0]]
            reporting.add_test_script(tests[0][0])
            data_dir_path = "/root"
            md5sums_before_full = {}
            LOG.debug("******************")
            kp = self.create_key_pair(
                tvaultconf.key_pair_name, keypair_cleanup=True)
            LOG.debug("Key_pair : " + str(kp))

            vm_id = self.create_vm(key_pair=kp, vm_cleanup=False)
            LOG.debug("VM ID : " + str(vm_id))
            time.sleep(30)

            floating_ip_1 = self.assign_floating_ips(vm_id, False)
            LOG.debug("Assigned floating IP : " + str(floating_ip_1))

            LOG.debug("Sleeping for 20 sec")
            time.sleep(20)

            self.data_ops(floating_ip_1, data_dir_path, 3)
            LOG.debug("Created data")

            md5sums_before_full = self.calcmd5sum(floating_ip_1, data_dir_path)
            LOG.debug("MD5sums for directory on original vm : " +
                      str(md5sums_before_full))

            workload_create = command_argument_string.workload_create + \
                " --instance instance-id=" + str(vm_id)
            rc = cli_parser.cli_returncode(workload_create)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-create command", tvaultconf.FAIL)
                raise Exception(
                    "Workload-create command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-create command", tvaultconf.PASS)
                LOG.debug("Workload-create command executed correctly")

            time.sleep(10)
            workload_id = query_data.get_workload_id(tvaultconf.workload_name)
            LOG.debug("Workload ID: " + str(workload_id))
            if(workload_id is not None):
                self.wait_for_workload_tobe_available(workload_id)
                if(self.getWorkloadStatus(workload_id) == "available"):
                    reporting.add_test_step("Create workload", tvaultconf.PASS)
                else:
                    reporting.add_test_step("Create workload", tvaultconf.FAIL)
                    raise Exception("Workload creation failed")
            else:
                reporting.add_test_step("Create workload", tvaultconf.FAIL)
                raise Exception("Workload creation failed")

            if (tvaultconf.cleanup):
                self.addCleanup(self.workload_delete, workload_id)

            ### Full snapshot ###

            snapshot_id = self.create_snapshot(workload_id, is_full=True)

            # Add some more data to files on VM
            ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip_1))
            self.addCustomfilesOnLinuxVM(ssh, data_dir_path, 2)
            ssh.close()
            md5sums_before_incremental = {}
            md5sums_before_incremental = self.calcmd5sum(
                floating_ip_1, data_dir_path)
            LOG.debug("\nMD5SUM after adding additional data before incremental snapshot : {}\n".format(
                md5sums_before_incremental))

            ### Incremental snapshot ###

            incr_snapshot_id = self.create_snapshot(workload_id, is_full=False)

            ### Selective restore ###

            rest_details = {}
            rest_details['rest_type'] = 'selective'
            rest_details['network_id'] = CONF.network.internal_network_id
            rest_details['subnet_id'] = self.get_subnet_id(
                CONF.network.internal_network_id)
            volumeslist = []
            rest_details['instances'] = {vm_id: volumeslist}

            payload = self.create_restore_json(rest_details)
            # Trigger selective restore
            restore_id_1 = self.snapshot_selective_restore(
                workload_id,
                snapshot_id,
                restore_name=tvaultconf.restore_name,
                restore_cleanup=True,
                instance_details=payload['instance_details'],
                network_details=payload['network_details'])
            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            if(self.getRestoreStatus(workload_id, snapshot_id, restore_id_1) == "available"):
                reporting.add_test_step("Selective restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("Selective restore", tvaultconf.FAIL)
                raise Exception("Selective restore failed")

            # Fetch instance details after restore
            vm_list = self.get_restored_vm_list(restore_id_1)
            LOG.debug("Restored vm(selective) ID : " + str(vm_list))
            time.sleep(60)
            floating_ip_2 = self.assign_floating_ips(vm_list[0], True)
            LOG.debug(
                "Floating ip assigned to selective restore vm -> " +
                str(floating_ip_2))
            md5sums_after_selective = {}
            ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip_2))
            md5sums_after_selective = self.calcmd5sum(
                floating_ip_2, data_dir_path)
            ssh.close()

            LOG.debug("MD5SUMS before restore")
            LOG.debug(md5sums_before_full[str(floating_ip_1)])
            LOG.debug("MD5SUMS after selective restore")
            LOG.debug(md5sums_after_selective[str(floating_ip_2)])

            if md5sums_before_full[str(
                floating_ip_1)] == md5sums_after_selective[str(floating_ip_2)]:
                LOG.debug("***MDSUMS MATCH***")
                reporting.add_test_step(
                    "Md5 Verification for volume", tvaultconf.PASS)
                reporting.set_test_script_status(tvaultconf.PASS)
            else:
                LOG.debug("***MDSUMS DON'T MATCH***")
                reporting.add_test_step(
                    "Md5 Verification for volume", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            restored_vm_details = []
            for id in range(len(vm_list)):
                restored_vm_details.append(self.get_vm_details(vm_list[id]))
            LOG.debug("Restored vm details list: " + str(restored_vm_details))

            vms_details_after_restore = self.get_vms_details_list(
                restored_vm_details)
            LOG.debug("VM details after restore: " +
                      str(vms_details_after_restore))
            # Compare the data before and after restore
            int_net_1_name = self.get_net_name(
                CONF.network.internal_network_id)
            for i in range(len(vms_details_after_restore)):
                if(vms_details_after_restore[i]['network_name'] == int_net_1_name):
                    reporting.add_test_step(
                        "Network verification for instance-" + str(i + 1), tvaultconf.PASS)
                    tests[0][1] = 1
                    reporting.test_case_to_write()
                else:
                    LOG.error("Expected network: " + str(int_net_1_name))
                    LOG.error("Restored network: " +
                              str(vms_details_after_restore[i]['network_name']))
                    reporting.add_test_step(
                        "Network verification for instance-" + str(i + 1), tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
                    reporting.test_case_to_write()

            ### In-place Restore ###

            rest_details = {}
            rest_details['rest_type'] = 'inplace'
            rest_details['instances'] = {vm_id: volumeslist}

            reporting.add_test_script(tests[1][0])
            # Create in-place restore with CLI command
            restore_command = command_argument_string.inplace_restore + \
                str(tvaultconf.restore_filename) + " " + str(snapshot_id)
            payload = self.create_restore_json(rest_details)
            restore_json = json.dumps(payload)
            LOG.debug("restore.json for inplace restore: " + str(restore_json))
            # Create Restore.json
            with open(tvaultconf.restore_filename, 'w') as f:
                f.write(str(yaml.safe_load(restore_json)))
            rc = cli_parser.cli_returncode(restore_command)
            if rc != 0:
                reporting.add_test_step(
                    "Triggering In-Place restore via CLI", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Triggering In-Place restore via CLI", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            # get restore id from database
            restore_id_2 = query_data.get_snapshot_restore_id(snapshot_id)
            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)

            # get in-place restore status
            if(self.getRestoreStatus(workload_id, snapshot_id, restore_id_2) == "available"):
                reporting.add_test_step("In-place restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("In-place restore", tvaultconf.FAIL)
                raise Exception("In-place restore failed")

            # Fetch instance details after restore
            vm_list = []
            vm_list = self.get_restored_vm_list(restore_id_2)
            LOG.debug("Restored vm(In-place) ID : " + str(vm_list))

            time.sleep(60)
            md5sums_after_inplace = {}
            ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip_1))
            md5sums_after_inplace = self.calcmd5sum(
                floating_ip_1, data_dir_path)
            ssh.close()

            LOG.debug("<----md5sums_before_full---->")
            LOG.debug(md5sums_before_full[str(floating_ip_1)])
            LOG.debug("<----md5sums_after_inplace---->")
            LOG.debug(md5sums_after_inplace[str(floating_ip_1)])

            if md5sums_before_full[str(
                floating_ip_1)] == md5sums_after_inplace[str(floating_ip_1)]:
                LOG.debug("***MDSUMS MATCH***")
                reporting.add_test_step(
                    "Md5 Verification for volume", tvaultconf.PASS)
                tests[1][1] = 1
                reporting.set_test_script_status(tvaultconf.PASS)
                reporting.test_case_to_write()
            else:
                LOG.debug("***MDSUMS DON'T MATCH***")
                reporting.add_test_step(
                    "Md5 Verification for volume", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                reporting.test_case_to_write()

            # Delete restore for snapshot
            if (tvaultconf.cleanup):
                self.addCleanup(self.restore_delete, workload_id,
                                snapshot_id, restore_id_2)

            ### One-click restore ###

            reporting.add_test_script(tests[2][0])

            # Delete the original instance
            self.delete_vm(vm_id)
            LOG.debug(
                "Instance deleted successfully for one click restore : " +
                str(vm_id))
            time.sleep(10)

            deleted = 1

            # Create one-click restore using CLI command
            restore_command = command_argument_string.oneclick_restore + " " + incr_snapshot_id
            rc = cli_parser.cli_returncode(restore_command)
            if rc != 0:
                reporting.add_test_step(
                    "Execute snapshot-oneclick-restore command",
                    tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute snapshot-oneclick-restore command",
                    tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            restore_id_3 = query_data.get_snapshot_restore_id(incr_snapshot_id)
            LOG.debug("Restore ID: " + str(restore_id_3))

            self.wait_for_snapshot_tobe_available(
                workload_id, incr_snapshot_id)
            if(self.getRestoreStatus(workload_id, incr_snapshot_id, restore_id_3) == "available"):
                reporting.add_test_step("One-click restore", tvaultconf.PASS)
                LOG.debug("One-click restore passed")
            else:
                reporting.add_test_step("One-click restore", tvaultconf.FAIL)
                LOG.debug("One-click restore failed")
                raise Exception("One-click restore failed")
            LOG.debug("One-click restore complete")

            # Fetch instance details after restore
            vm_list = []
            vm_list = self.get_restored_vm_list(restore_id_3)
            LOG.debug("Restored vms : " + str(vm_list))

            md5sums_after_1clickrestore = {}
            ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip_1))
            md5sums_after_1clickrestore = self.calcmd5sum(
                floating_ip_1, data_dir_path)
            LOG.debug("MD5SUMS after one click restore : {}".format(
                md5sums_after_1clickrestore))
            ssh.close()

            if md5sums_before_incremental[str(
                floating_ip_1)] == md5sums_after_1clickrestore[str(floating_ip_1)]:
                LOG.debug("***MDSUMS MATCH***")
                reporting.add_test_step(
                    "Md5 Verification for volume", tvaultconf.PASS)
                tests[2][0] = 1
                reporting.set_test_script_status(tvaultconf.PASS)
                reporting.test_case_to_write()
            else:
                LOG.debug("***MDSUMS DON'T MATCH***")
                reporting.add_test_step(
                    "Md5 Verification for volume", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                reporting.test_case_to_write()

            restored_volumes = []
            restored_volumes = self.get_restored_volume_list(restore_id_3)
            LOG.debug("Restored volumes : ")
            LOG.debug(restored_volumes)

            if (tvaultconf.cleanup):
                self.addCleanup(self.restore_delete, workload_id,
                                incr_snapshot_id, restore_id_3)
                time.sleep(30)
                self.addCleanup(self.delete_restored_vms,
                                vm_list, restored_volumes)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            if (deleted == 0):
                try:
                    self.delete_vm(vm_id)
                except BaseException:
                    pass
            for test in tests:
                if test[1] != 1:
                    reporting.add_test_script(test[0])
                    reporting.set_test_script_status(tvaultconf.FAIL)
                    reporting.test_case_to_write()
