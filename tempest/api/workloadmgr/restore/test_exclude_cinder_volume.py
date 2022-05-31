import json
import os
import sys
import time
import paramiko

import yaml
from oslo_log import log as logging

from tempest import command_argument_string
from tempest import config
from tempest import reporting
from tempest.api.workloadmgr import base
from tempest import tvaultconf
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

    def assign_floating_ips(self, fip, vm_id, cleanup):
        self.set_floating_ip(str(fip), vm_id, floatingip_cleanup=cleanup)
        return fip

    def calcmd5sum(self, flip, mount_point):
        mdb = {}
        ssh = self.SshRemoteMachineConnectionWithRSAKey(str(flip))
        mdb[str(flip)] = self.calculatemmd5checksum(ssh, mount_point)
        ssh.close()
        return mdb

    def data_ops_on_mount_point(self, flo_ip, mount_point, file_count):
        global volumes
        ssh = self.SshRemoteMachineConnectionWithRSAKey(str(flo_ip))
        self.install_qemu(ssh)
        self.execute_command_disk_create(
            ssh, str(flo_ip), [volumes[0]], [mount_point])
        self.execute_command_disk_mount(
            ssh, str(flo_ip), [volumes[0]], [mount_point])
        self.addCustomfilesOnLinuxVM(ssh, mount_point, file_count)
        ssh.close()

    def data_ops_delete_files(self, flo_ip, mount_point, file_count):
        ssh = self.SshRemoteMachineConnectionWithRSAKey(str(flo_ip))
        self.deleteSomefilesOnLinux(ssh, mount_point, file_count)

    def check_mount_cmd_status(self, floating_ip_addr, volumes, mount_point):
        max_retries = 0
        cmd_err = ""
        cmd_output = ""
        ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip_addr))
        time.sleep(5)
        cmd = "sudo mount -v " + volumes[0] + "1 " + mount_point[0] + " "
        LOG.debug("Command to mount volume " + str(cmd))
        stdin, stdout, stderr = ssh.exec_command(
            cmd)
        time.sleep(15)
        while not stdout.channel.exit_status_ready():
            time.sleep(3)
            LOG.debug("sleeping for 3sec")
            max_retries += 1
            if max_retries == 10:
                reporting.add_test_step("Max retries exceeded for mount command output.", tvaultconf.FAIL)
                raise Exception("Max retries exceeded for mount command output.")

        # read command output and error
        cmd_err = stderr.readlines()
        cmd_output = stdout.readlines()
        LOG.debug("COMMAND error  " + str(cmd_err))
        LOG.debug("COMMAND output " + str(cmd_output))

        cmd_err = str(cmd_err)
        if len(cmd_err) > 0:
            err_msg = ["special device", "does not exist"]
            # look for all sub-string in error message.
            result = all(x in cmd_err for x in err_msg)
            if (result):
                reporting.add_test_step("Volume mount afterrestore",
                                        tvaultconf.PASS)
                reporting.set_test_script_status(tvaultconf.PASS)
            else:
                reporting.add_test_step("Volume mount after restore", tvaultconf.FAIL)
                # close ssh connection
                ssh.close()
                return False
        else:
            reporting.add_test_step("Volume mount after restore", tvaultconf.FAIL)
            # close ssh connection
            ssh.close()
            return False

        # close ssh connection
        ssh.close()
        return True

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

    @decorators.attr(type='workloadmgr_cli')
    def test_exclude_cinder_volume_backup(self):
        try:
            deleted = 0
            mount_point = ["mount_data_AFolder"]
            global volumes
            ## VM and Workload ###
            tests = [['tempest.api.workloadmgr.restore.test_volume_exclsion_Selective_restore',
                      0],
                     ['tempest.api.workloadmgr.restore.test_volume_exclusion_Inplace_restore',
                      0],
                     ['tempest.api.workloadmgr.restore.test_volume_exclusion_Oneclick_restore',
                      0]]

            reporting.add_test_script(tests[0][0])

            fip = self.get_floating_ips()
            if len(fip) < 2:
                raise Exception("Floating ips unavailable")

            # create key_pair value
            kp = self.create_key_pair(
                tvaultconf.key_pair_name, keypair_cleanup=True)
            LOG.debug("Key_pair : " + str(kp))

            # create vm
            vm_id = self.create_vm(key_pair=kp, vm_cleanup=True)
            LOG.debug("VM ID : " + str(vm_id))
            time.sleep(30)

            # create volume
            volume_id = self.create_volume(volume_cleanup=False)
            LOG.debug("Volume ID: " + str(volume_id))
            volumes = tvaultconf.volumes_parts

            # attach volume to vm
            self.attach_volume(volume_id, vm_id, attach_cleanup=False)
            LOG.debug("Volume attached")

            # assign floating ip
            floating_ip_1 = self.assign_floating_ips(fip[0], vm_id, False)
            LOG.debug("Assigned floating IP : " + str(floating_ip_1))
            time.sleep(20)

            # add some data to volume attached
            self.data_ops_on_mount_point(floating_ip_1, mount_point[0], 3)
            LOG.debug("Created disk and mounted the attached volume")

            # calculate checksum
            md5sums_before_full = {}
            md5sums_before_full = self.calcmd5sum(
                floating_ip_1, mount_point[0])
            LOG.debug("MD5sums for directory on original vm : " +
                      str(md5sums_before_full))

            # update volume metadata
            body = self.modify_volume_metadata(
                volume_id, tvaultconf.enable_cinder_volume_exclusion)
            LOG.debug("Response to update volume metadata req: " + str(body))

            # Create workload using CLI
            workload_create = command_argument_string.workload_create + \
                              " --instance instance-id=" + str(vm_id)

            rc = cli_parser.cli_returncode(workload_create)

            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-create command using cli",
                    tvaultconf.FAIL)
                raise Exception(
                    "Command workload create did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-create command using cli",
                    tvaultconf.PASS)

            time.sleep(10)

            # check workload status
            wid = query_data.get_workload_id_in_creation(tvaultconf.workload_name)
            LOG.debug("Workload ID: " + str(wid))
            if (wid is not None):
                self.wait_for_workload_tobe_available(wid)
                if (self.getWorkloadStatus(wid) == "available"):
                    reporting.add_test_step(
                        "Create workload using cli", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Create workload using cli", tvaultconf.FAIL)
                    raise Exception("Create workload using cli failed.")
            else:
                reporting.add_test_step(
                    "Create workload using cli", tvaultconf.FAIL)
                raise Exception("Create workload using cli failed.")

            # take full snapshot
            snapshot_id = self.workload_snapshot(wid, True)

            self.wait_for_workload_tobe_available(wid)
            snapshot_status = self.getSnapshotStatus(wid, snapshot_id)

            if (snapshot_status == "available"):
                LOG.debug("Full snapshot created.")
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
            else:
                reporting.add_test_step("Create full snapshot", tvaultconf.FAIL)
                raise Exception("Full snapshot creation failed.")

            # delete few files from original vm instance
            self.data_ops_delete_files(floating_ip_1, mount_point[0], 1)
            time.sleep(10)

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
                wid,
                snapshot_id,
                restore_name=tvaultconf.restore_name,
                restore_cleanup=True,
                instance_details=payload['instance_details'],
                network_details=payload['network_details'])

            self.wait_for_snapshot_tobe_available(wid, snapshot_id)
            if (self.getRestoreStatus(wid, snapshot_id, restore_id_1) == "available"):
                reporting.add_test_step("Selective restore of snapshot id = {} ".format(
                    snapshot_id), tvaultconf.PASS)
            else:
                reporting.add_test_step("Selective restore of snapshot id = {} ".format(
                    snapshot_id), tvaultconf.FAIL)
                raise Exception("Selective restore failed")

            # Fetch instance details after restore
            vm_list = self.get_restored_vm_list(restore_id_1)
            LOG.debug("Restored vm(selective) ID : " + str(vm_list))

            time.sleep(60)

            # assign floating ip
            floating_ip_2 = self.assign_floating_ips(fip[1], vm_list[0], True)
            LOG.debug(
                "Floating ip assigned to selective restore vm -> " +
                str(floating_ip_2))

            # connect to restored vm and try to mount volume
            cmd_status = self.check_mount_cmd_status(floating_ip_2, volumes, mount_point)
            if cmd_status:
                tests[0][1] = 1
            else:
                raise Exception("Mount command for excluded volume is successful. Test case failed.")

            ### In-place restore ###
            reporting.add_test_script(tests[1][0])

            rest_details = {}
            rest_details['rest_type'] = 'inplace'
            rest_details['instances'] = {vm_id: volumeslist}

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
            self.wait_for_snapshot_tobe_available(wid, snapshot_id)

            # get in-place restore status
            if (self.getRestoreStatus(wid, snapshot_id, restore_id_2) == "available"):
                reporting.add_test_step("In-place restore of snapshot id = {} ".format(
                    snapshot_id), tvaultconf.PASS)
            else:
                reporting.add_test_step("In-place restore of snapshot id = {} ".format(
                    snapshot_id), tvaultconf.FAIL)
                raise Exception("In-place restore failed")

            # Fetch instance details after restore
            vm_list = []
            vm_list = self.get_restored_vm_list(restore_id_2)
            LOG.debug("Restored vm(In-place) ID : " + str(vm_list))

            time.sleep(60)

            # calculate md5sum
            md5sums_after_inplace = {}
            md5sums_after_inplace = self.calcmd5sum(
                floating_ip_1, mount_point[0])
            LOG.debug("MD5sums for directory on original vm after in-place restore : " +
                      str(md5sums_after_inplace))

            if md5sums_before_full[str(
                    floating_ip_1)] != md5sums_after_inplace[str(floating_ip_1)]:
                reporting.add_test_step("In-place restore checksum verification", tvaultconf.PASS)
                tests[1][1] = 1
            else:
                reporting.add_test_step("In-place restore checksum verification", tvaultconf.FAIL)
                raise Exception("MD5checksum matched. test case failed.")

            # Delete restore for snapshot
            if (tvaultconf.cleanup):
                self.addCleanup(self.restore_delete, wid,
                                snapshot_id, restore_id_2)

            ### One-click restore ###
            reporting.add_test_script(tests[2][0])

            # Delete the original instance
            self.delete_vm(vm_id)
            LOG.debug(
                "Instance deleted successfully for one click restore : " +
                str(vm_id))

            time.sleep(10)

            # Delete volume of original instance
            self.delete_volume(volume_id)
            LOG.debug("Volume of original instance deleted")
            deleted = 1

            # Create one-click restore using CLI command
            restore_command = command_argument_string.oneclick_restore + " " + snapshot_id
            rc = cli_parser.cli_returncode(restore_command)
            if rc != 0:
                reporting.add_test_step(
                    "Oneclick-restore cli command",
                    tvaultconf.FAIL)
                raise Exception("One-click restore command did not executed correctly")
            else:
                reporting.add_test_step(
                    "Oneclick-restore cli command",
                    tvaultconf.PASS)
                LOG.debug("One-click restore command executed successfully")

            restore_id_3 = query_data.get_snapshot_restore_id(snapshot_id)
            LOG.debug("Restore ID: " + str(restore_id_3))

            self.wait_for_snapshot_tobe_available(
                wid, snapshot_id)

            # get one-click restore status
            if (self.getRestoreStatus(wid, snapshot_id, restore_id_3) == "available"):
                reporting.add_test_step("One-click restore of snapshot id = {} ".format(
                    snapshot_id), tvaultconf.PASS)
                LOG.debug("One-click restore passed")
            else:
                reporting.add_test_step("One-click restore of snapshot id = {} ".format(
                    snapshot_id), tvaultconf.FAIL)
                LOG.debug("One-click restore failed")
                raise Exception("One-click restore failed")

            # Fetch instance details after restore
            vm_list = []
            vm_list = self.get_restored_vm_list(restore_id_3)
            LOG.debug("Restored vms : " + str(vm_list))

            time.sleep(60)

            # connect to restored vm and try to mount volume
            cmd_status = self.check_mount_cmd_status(floating_ip_1, volumes, mount_point)
            if cmd_status:
                tests[2][1] = 1
            else:
                raise Exception("Mount command for excluded volume is successful. Test case failed.")


        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            for test in tests:
                if test[1] != 1:
                    reporting.add_test_script(test[0])
                    reporting.set_test_script_status(tvaultconf.FAIL)
                    reporting.test_case_to_write()

            if (deleted == 0):
                try:
                    self.delete_vm(vm_id)
                except BaseException:
                    pass

                time.sleep(10)

                try:
                    self.delete_volume(volume_id)
                except BaseException:
                    pass

            reporting.test_case_to_write()

