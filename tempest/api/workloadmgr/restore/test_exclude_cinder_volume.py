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


    def data_ops_on_mount_point(self, flo_ip, mount_point, file_count):
        global volumes
        ssh = self.SshRemoteMachineConnectionWithRSAKey(str(flo_ip))
        stdin, stdout, stderr = ssh.exec_command(
            "sudo apt install qemu-guest-agent")
        self.execute_command_disk_create(
            ssh, str(flo_ip), [volumes[0]], [mount_point])
        self.execute_command_disk_mount(
            ssh, str(flo_ip), [volumes[0]], [mount_point])
        self.addCustomfilesOnLinuxVM(ssh, mount_point, file_count)
        ssh.close()


    @decorators.attr(type='workloadmgr_cli')
    def test_exclude_cinder_volume_backup(self):
        try:
            deleted = 0
            global volumes
            ## VM and Workload ###
            tests = [['tempest.api.workloadmgr.restore.add_metadata_to_exclude_cinder_volume_from_backup',
                      0],
                     ['tempest.api.workloadmgr.restore.check_volume_status_after_restore',
                      0]
                     ]

            reporting.add_test_script(tests[0][0])

            #create key_pair value 
            kp = self.create_key_pair(
                tvaultconf.key_pair_name, keypair_cleanup=True)
            LOG.debug("Key_pair : " + str(kp))

            #create vm
            vm_id = self.create_vm(key_pair=kp, vm_cleanup=False)
            LOG.debug("VM ID : " + str(vm_id))
            time.sleep(30)

            #create volume
            volume_id = self.create_volume(volume_cleanup=False)
            LOG.debug("Volume ID: " + str(volume_id))
            volumes = tvaultconf.volumes_parts

            #attach volume to vm
            self.attach_volume(volume_id, vm_id, attach_cleanup=False)
            LOG.debug("Volume attached")

            #assign floating ip
            floating_ip_1 = self.assign_floating_ips(vm_id, False)
            LOG.debug("Assigned floating IP : " + str(floating_ip_1))
            time.sleep(20)

            #add some data to volume attached
            mount_point = ["mount_data_AFolder"]
            self.data_ops_on_mount_point(floating_ip_1, mount_point[0], 3)
            LOG.debug("Created disk and mounted the attached volume")

            #add metadata to the volume...
            custom_metadata = {"exclude_from_backup": "True"
                        }

            body = self.volumes_client.update_volume_metadata(
            volume_id, custom_metadata)['metadata']

            LOG.debug("Requested to update metadata: " + str(body))

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

            #check workload status
            wid = query_data.get_workload_id_in_creation(tvaultconf.workload_name)
            LOG.debug("Workload ID: " + str(wid))
            if(wid is not None):
                self.wait_for_workload_tobe_available(wid)
                if(self.getWorkloadStatus(wid) == "available"):
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


            #take full snapshot
            snapshot_id = self.workload_snapshot(wid, True)

            self.wait_for_workload_tobe_available(wid)
            snapshot_status = self.getSnapshotStatus(wid, snapshot_id)

            if (snapshot_status == "available"):
                LOG.debug("Full snapshot created.")
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                tests[0][1] = 1
            else:
                reporting.add_test_step("Create full snapshot", tvaultconf.FAIL)
                raise Exception("Full snapshot creation failed.")

            reporting.test_case_to_write()

            reporting.add_test_script(tests[1][0])
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
            if(self.getRestoreStatus(wid, snapshot_id, restore_id_1) == "available"):
                reporting.add_test_step("Selective restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("Selective restore", tvaultconf.FAIL)
                raise Exception("Selective restore failed")

            # Fetch instance details after restore
            vm_list = self.get_restored_vm_list(restore_id_1)
            LOG.debug("Restored vm(selective) ID : " + str(vm_list))

            time.sleep(60)

            #assign floating ip
            floating_ip_2 = self.assign_floating_ips(vm_list[0], True)
            LOG.debug(
                "Floating ip assigned to selective restore vm -> " +
                str(floating_ip_2))

            #connect to restored vm and try to mount volume
            max_retries = 0
            cmd_err = ""
            cmd_output = ""
            ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip_2))
            cmd = "sudo mount "+volumes[0]+"1 "+mount_point[0]+" "
            LOG.debug("Command to mount volume" + str(cmd))
            stdin, stdout, stderr = ssh.exec_command(
            cmd)
            time.sleep(5)
            while not stdout.channel.exit_status_ready():
                time.sleep(3)
                max_retries += 1
                if max_retries == 10:
                    reporting.add_test_step("Max retries exceeded to get command output.", tvaultconf.FAIL)
                    raise Exception("Max retries exceeded to get command output.")

            #read command output and error
            cmd_err = stderr.readlines()
            cmd_output = stdout.readlines()
            LOG.debug("COMMAND error  " + str(cmd_err))
            LOG.debug("COMMAND output " + str(cmd_output))

            cmd_err = str(cmd_err)
            if len(cmd_err) > 0:
                err_msg = ["special device","does not exist"]
                # look for all sub-string in error message.
                result = all(x in cmd_err for x in err_msg)
                if (result):
                    reporting.add_test_step("Volume status post restore for metadata exclude_from_backup",
                                            tvaultconf.PASS)
                    reporting.set_test_script_status(tvaultconf.PASS)
                    tests[1][1] = 1
                else:
                    reporting.add_test_step("Different error occurred than expected.", tvaultconf.FAIL)
                    raise Exception("Different error occurred while performing mount operation.")
            else:
                reporting.add_test_step("Different error occurred than expected.", tvaultconf.FAIL)
                raise Exception("Mount command successful, test case failed.")

            #close ssh connection
            ssh.close()


        except Exception as e:
            for test in tests:
                if test[1] != 1:
                    reporting.add_test_script(test[0])
                    reporting.set_test_script_status(tvaultconf.FAIL)
                    reporting.test_case_to_write()


        finally:
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


