import json
import os
import sys
import time
import paramiko

import yaml
from oslo_log import log as logging

import testtools
from testtools import matchers

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
        return (fip[0])

    def data_ops_for_bootdisk(self, flo_ip, data_dir_path, file_count):
        ssh = self.SshRemoteMachineConnectionWithRSAKey(str(flo_ip))
        self.install_qemu(ssh)
        self.addCustomfilesOnLinuxVM(ssh, data_dir_path, file_count)
        ssh.close()

    def execute_cmd_on_remote_machine(self, flo_ip, cmd):
        stdin, stdout, strerr = ""
        ssh = self.SshRemoteMachineConnectionWithRSAKey(str(flo_ip))
        self.install_qemu(ssh)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        time.sleep(10)
        ssh.close()
        return stdin, stdout, stderr

    @decorators.attr(type='workloadmgr_cli')
    def exclude_bootdisk_backup(self):
        try:
            deleted = 0
            ## VM and Workload ###
            tests = [['tempest.api.workloadmgr.restore.add_metadata_exclude_boot_disk_from_backup',
                      0],
                     ['tempest.api.workloadmgr.restore.search_files_in_snapshot_after_adding_metadata',
                      0],
                     ['tempest.api.workloadmgr.restore.remove_metadata_exclude_boot_disk_from_backup',
                      0],
                     ['tempest.api.workloadmgr.restore.search_files_in_snapshot_after_removing_metadata',
                      0]
                     ]
            reporting.add_test_script(tests[0][0])

            # create key_pair value
            kp = self.create_key_pair(
                tvaultconf.key_pair_name, keypair_cleanup=True)
            LOG.debug("Key_pair : " + str(kp))

            # create vm
            vm_id = self.create_vm(key_pair=kp, vm_cleanup=True)
            LOG.debug("VM ID : " + str(vm_id))
            time.sleep(30)

            # assign floating ip
            floating_ip_1 = self.assign_floating_ips(vm_id, False)
            LOG.debug("Assigned floating IP : " + str(floating_ip_1))

            time.sleep(20)

            # add some data to boot disk...
            data_dir_path = "/opt"
            self.data_ops_for_bootdisk(floating_ip_1, data_dir_path, 3)

            # create a workload...
            # Create workload with scheduler disabled using CLI
            workload_create = command_argument_string.workload_create + \
                              " --instance instance-id=" + str(vm_id) + \
                              " --metadata " + str(tvaultconf.enable_bootdisk_exclusion)
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
            wid = query_data.get_workload_id_in_creation(tvaultconf.workload_name)
            LOG.debug("Workload ID: " + str(wid))
            if (wid is not None):
                self.wait_for_workload_tobe_available(wid)
                if (self.getWorkloadStatus(wid) == "available"):
                    reporting.add_test_step(
                        "Check workload status", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Check workload status", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                raise Exception("Create workload failed.")

            snapshot_id = self.workload_snapshot(wid, True)

            self.wait_for_workload_tobe_available(wid)
            snapshot_status = self.getSnapshotStatus(wid, snapshot_id)

            if (snapshot_status == "available"):
                LOG.debug("Full snapshot created.")
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                tests[0][1] = 1
            else:
                reporting.add_test_step("Create full snapshot", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("Full snapshot created with unencrypted and encrypted volume")

            reporting.test_case_to_write()

            reporting.add_test_script(tests[1][0])
            # check the filesearch status...
            # perform file search on snapshot_id to check if file present in backup or not.
            filecount_in_snapshots = {snapshot_id: 1}
            filename = "/opt/File_1"

            filesearch_id = self.filepath_search(vm_id, filename, snapshot_id)
            LOG.debug("filesearch_id =" + str(filesearch_id))

            try:
                snapshot_wise_filecount = self.verifyFilepath_Search(filesearch_id, filename)
                LOG.debug("snapshot_wise_filecount =" + str(snapshot_wise_filecount))
                for snap_id in filecount_in_snapshots.keys():
                    if snapshot_wise_filecount[snap_id] == filecount_in_snapshots[snap_id]:
                        filesearch_status = True
                    else:
                        filesearch_status = False

                if filesearch_status:
                    LOG.debug(
                        "Custom created file found under /opt/ even after adding metadata exclude_boot_disk_from_backup")
                    reporting.add_test_step(
                        "Search file on snapshot",
                        tvaultconf.FAIL)
                else:
                    LOG.debug(
                        "Custom created file not found under /opt/ after adding metadata exclude_boot_disk_from_backup")
                    reporting.add_test_step(
                        "Search file on snapshot",
                        tvaultconf.PASS)

            except Exception as e:
                reporting.add_test_step(
                    "Search file on snapshot", tvaultconf.FAIL)

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

            # connect to remote machine to check file on restored vm instance.
            cmd = 'sudo ls -lrth /opt/File_1'
            stdin, stdout, stderr = self.execute_cmd_on_remote_machine(floating_ip_2, cmd)

            output = stdout.read().decode('utf-8').strip()
            error = stderr.read().decode('utf-8').strip()

            LOG.debug("Output: " + str(output))
            LOG.debug("Error: " + str(error))

            if error:
                err_msg = ["No such file or directory"]
                result = all(x in error for x in err_msg)
                if (result):
                    reporting.add_test_step("Search files on restored vm instance",
                                            tvaultconf.PASS)
                    reporting.set_test_script_status(tvaultconf.PASS)
                    tests[1][1] = 1
                else:
                    reporting.add_test_step("Search files on restored vm instance",
                                            tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                LOG.debug("File present on restored instance")
                reporting.add_test_step("Search files on restored vm instance",
                                        tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # write the test step into test case - filesearch.
            # Remove metadata...
            reporting.test_case_to_write()

            reporting.add_test_script(tests[2][0])

            # add some more data and remove metadata for verification..
            cmd = 'sudo mkdir -p /opt/testfolder'
            stdin, stdout, stderr = self.execute_cmd_on_remote_machine(floating_ip_1, cmd)
            time.sleep(10)
            output = stdout.read().decode('utf-8').strip()
            error = stderr.read().decode('utf-8').strip()
            LOG.debug("Output: " + str(output))
            LOG.debug("Error: " + str(error))

            # Add more data to /opt/ directory...
            data_dir_path1 = "/opt/testfolder"
            self.data_ops_for_bootdisk(floating_ip_1, data_dir_path1, 3)
            LOG.debug("Created Additional Data")

            # as we have removed the metadata, so check if the files created are present in backup instance or not.
            # create an instance now...
            workload_modify = command_argument_string.workload_modify + \
                              str(wid) + \
                              " --metadata " + str(tvaultconf.disable_bootdisk_exclusion)

            rc = cli_parser.cli_returncode(workload_modify)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-modify command", tvaultconf.FAIL)
                raise Exception(
                    "Workload-modify command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-modify command", tvaultconf.PASS)
                LOG.debug("Workload-modify command executed correctly")

            # sleep for 10 sec for getting instance created...
            time.sleep(10)

            # check the workload status...
            workload_id = query_data.get_workload_id(tvaultconf.workload_name)
            LOG.debug("Workload ID: " + str(workload_id))
            if (workload_id is not None):
                self.wait_for_workload_tobe_available(workload_id)
                if (self.getWorkloadStatus(workload_id) == "available"):
                    reporting.add_test_step("Check workload status", tvaultconf.PASS)
                else:
                    reporting.add_test_step("Check workload status", tvaultconf.FAIL)
                    raise Exception("Workload creation failed")
            else:
                reporting.add_test_step("Check workload status", tvaultconf.FAIL)
                raise Exception("Workload creation failed")

            # Take a full snapshot of instance created above
            snapshot_id_1 = self.workload_snapshot(workload_id, True)

            self.wait_for_workload_tobe_available(workload_id)
            snapshot_status = self.getSnapshotStatus(workload_id, snapshot_id)

            if (snapshot_status == "available"):
                LOG.debug("Full snapshot created.")
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                tests[2][1] = 1
            else:
                reporting.add_test_step("Create full snapshot", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("Full snapshot created with unencrypted and encrypted volume")

            reporting.test_case_to_write()

            reporting.add_test_script(tests[3][0])
            # check the filesearch status...
            # perform file search on snapshot_id to check if file present in backup or not.
            filecount_in_snapshots = {snapshot_id_1: 1}
            filename = "/opt/testfolder/File_1"

            filesearch_id = self.filepath_search(vm_id, filename, snapshot_id_1)
            LOG.debug("filesearch_id =" + str(filesearch_id))

            try:
                snapshot_wise_filecount = self.verifyFilepath_Search(filesearch_id, filename)
                LOG.debug("snapshot_wise_filecount =" + str(snapshot_wise_filecount))
                for snap_id in filecount_in_snapshots.keys():
                    if snapshot_wise_filecount[snap_id] == filecount_in_snapshots[snap_id]:
                        filesearch_status = True
                    else:
                        filesearch_status = False

                if filesearch_status:
                    LOG.debug(
                        "Custom created file found under /opt/ even after adding metadata exclude_boot_disk_from_backup")
                    reporting.add_test_step(
                        "Search file on snapshot",
                        tvaultconf.PASS)
                    tests[3][1] = 1
                else:
                    LOG.debug(
                        "Custom created file not found under /opt/ after adding metadata exclude_boot_disk_from_backup")
                    reporting.add_test_step(
                        "Search file on snapshot",
                        tvaultconf.FAIL)

            except Exception as e:
                reporting.add_test_step(
                    "Verification of Filepath search", tvaultconf.FAIL)

            # write the test step into test case - filesearch.
            reporting.test_case_to_write()


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


