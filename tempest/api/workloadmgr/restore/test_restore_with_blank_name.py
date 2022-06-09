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
            LOG.debug("{} snapshot command execution failed.".format(str(substitution)))
            raise Exception(
                "Command did not execute correctly for full snapshot")

        if snapshot_execution == 'pass':
            reporting.add_test_step("{} snapshot".format(
                substitution), tvaultconf.PASS)
        else:
            LOG.debug("{} snapshot failed".format(str(substitution)))
            raise Exception("Full snapshot failed")
        return(snapshot_id)


    @decorators.attr(type='workloadmgr_cli')
    def test_restore_with_blank_name(self):
        try:
            deleted = 0
            global volumes
            ## VM and Workload ###
            tests = [['tempest.api.workloadmgr.restore.test_inplace_restore_with_blank_name',
                      0],
                     ['tempest.api.workloadmgr.restore.test_oneclick_restore_with_blank_name',
                      0],
                     ['tempest.api.workloadmgr.restore.test_selective_restore_with_blank_name',
                      0]]

            reporting.add_test_script(tests[0][0])

            # create key_pair value
            kp = self.create_key_pair(
                tvaultconf.key_pair_name, keypair_cleanup=True)
            LOG.debug("Key_pair : " + str(kp))

            # create vm
            vm_id = self.create_vm(key_pair=kp, vm_cleanup=True)
            LOG.debug("VM ID : " + str(vm_id))
            time.sleep(30)

            # Create workload using CLI
            workload_create = command_argument_string.workload_create + \
                              " --instance instance-id=" + str(vm_id)

            rc = cli_parser.cli_returncode(workload_create)

            if rc != 0:
                LOG.debug("Execute workload-create command using cli")
                raise Exception(
                    "Execute workload-create command using cli")
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
                    LOG.debug("Create workload using cli passed.")
                    reporting.add_test_step(
                        "Create workload using cli", tvaultconf.PASS)
                else:
                    LOG.debug("Create workload using cli failed.")
                    raise Exception("Create workload using cli")
            else:
                LOG.debug("Create workload using cli failed.")
                raise Exception("Create workload using cli")

            # take full snapshot
            snapshot_id = self.create_snapshot(wid, is_full=True)

            self.wait_for_workload_tobe_available(wid)
            snapshot_status = self.getSnapshotStatus(wid, snapshot_id)

            if (snapshot_status == "available"):
                LOG.debug("Full snapshot created.")
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
            else:
                LOG.debug("Full snapshot creation failed.")
                raise Exception("Create full snapshot")


            ### In-place restore ###

            volumeslist = []
            rest_details = {}
            rest_details['rest_type'] = 'inplace'
            rest_details['instances'] = {vm_id: volumeslist}

            payload = self.create_restore_json(rest_details)
            restore_json = json.dumps(payload)
            LOG.debug("restore.json for inplace restore: " + str(restore_json))
            # Create Restore.json
            with open(tvaultconf.restore_filename, 'w') as f:
                f.write(str(yaml.safe_load(restore_json)))

            # Create in-place restore with CLI command
            restore_command = command_argument_string.inplace_restore_with_blank_name + \
                              str(tvaultconf.restore_filename) + " " + str(snapshot_id)
            LOG.debug("Inplace Restore_command is :=" + str(restore_command))

            rc = cli_parser.cli_returncode(restore_command)

            if rc != 0:
                LOG.debug("In-Place restore cli command with blank name command")
                raise Exception("In-Place restore cli command with blank name command")
            else:
                reporting.add_test_step(
                    "In-Place restore cli command with blank name command", tvaultconf.PASS)
                LOG.debug("In-Place restore cli command with blank name executed correctly")


            # get restore id from database
            restore_id_1 = query_data.get_snapshot_restore_id(snapshot_id)

            self.wait_for_snapshot_tobe_available(wid, snapshot_id)

            # get in-place restore status
            if (self.getRestoreStatus(wid, snapshot_id, restore_id_1) == "available"):
                reporting.add_test_step("In-place restore of full snapshot", tvaultconf.PASS)
                reporting.set_test_script_status(tvaultconf.PASS)
                tests[0][1] = 1

            else:
                LOG.debug("In-place restore of full snapshot")
                raise Exception("In-place restore of full snapshot")

            # Fetch instance details after restore
            inplace_vm_list = []
            inplace_vm_list = self.get_restored_vm_list(restore_id_1)
            LOG.debug("Restored vm(In-place) ID : " + str(inplace_vm_list))

            reporting.test_case_to_write()


            ### One-click restore ###
            reporting.add_test_script(tests[1][0])

            # Delete the original instance
            self.delete_vm(vm_id)
            LOG.debug(
                "Instance deleted successfully for one click restore : " +
                str(vm_id))

            deleted = 1
            time.sleep(10)

            # Create one-click restore using CLI command
            restore_command = command_argument_string.oneclick_restore_with_blank_name + str(snapshot_id)
            LOG.debug("Restore_command is :=" + str(restore_command))

            rc = cli_parser.cli_returncode(restore_command)
            if rc != 0:
                LOG.debug("One-click restore cli with blank name command failed to execute")
                raise Exception("One-click restore cli with blank name command")
            else:
                reporting.add_test_step(
                    "One-click-restore cli with blank name command",
                    tvaultconf.PASS)
                LOG.debug("One-click restore with blank name command executed successfully")

            restore_id_2 = query_data.get_snapshot_restore_id(snapshot_id)

            self.wait_for_snapshot_tobe_available(
                wid, snapshot_id)

            # get one-click restore status
            if (self.getRestoreStatus(wid, snapshot_id, restore_id_2) == "available"):
                LOG.debug("One-click restore of full snapshot passed.")
                reporting.add_test_step("One-click restore of full snapshot", tvaultconf.PASS)
                reporting.set_test_script_status(tvaultconf.PASS)
                tests[1][1] = 1
            else:
                LOG.debug("One-click restore of full snapshot failed.")
                raise Exception("One-click restore of full snapshot")

            # Fetch instance details after restore
            oneclick_vm_list = []
            oneclick_vm_list = self.get_restored_vm_list(restore_id_1)
            LOG.debug("Restored vms list: " + str(oneclick_vm_list))

            reporting.test_case_to_write()


            ### Selective restore ###
            reporting.add_test_script(tests[2][0])

            instance_details = []
            volumeslist = []
            vm_name = 'tempest_test_vm_'+str(vm_id)+'_selectively_restored'
            rest_details = {'id': str(vm_id),
                            'availability_zone': CONF.volume.volume_availability_zone,
                            'include': True,
                            'restore_boot_disk': True,
                            'name': vm_name,
                            'vdisk':volumeslist}

            instance_details.append(rest_details)

            #payload to pass - selective restore cli command.
            payload = {"type": "openstack",
                       "oneclickrestore": False,
                       "openstack": {"instances": instance_details,
                                     "networks_mapping": {"networks": []},
                                     "restore_topology": True},
                       "restore_type": "selective"}


            restore_json = json.dumps(payload)
            LOG.debug("restore.json for selective restore: " + str(restore_json))

            # Create Restore.json
            with open(tvaultconf.restore_filename, 'w') as f:
                f.write(str(yaml.safe_load(restore_json)))

            # Create selective restore with CLI command
            restore_command = command_argument_string.selective_restore_with_blank_name + \
                              str(tvaultconf.restore_filename) + " " + str(snapshot_id)
            LOG.debug("Restore_command for selective restore :=" + str(restore_command))

            rc = cli_parser.cli_returncode(restore_command)
            if rc != 0:
                LOG.debug("Selective restore cli command with blank name command")
                raise Exception("Selective restore cli command with blank name command")
            else:
                reporting.add_test_step(
                    "Selective restore cli with blank name command", tvaultconf.PASS)
                LOG.debug("Selective restore Command executed correctly")


            restore_id = query_data.get_snapshot_restore_id(snapshot_id)

            self.wait_for_snapshot_tobe_available(wid, snapshot_id)

            if (self.getRestoreStatus(wid, snapshot_id, restore_id) == "available"):
                reporting.add_test_step("Selective restore of full snapshot", tvaultconf.PASS)
                reporting.set_test_script_status(tvaultconf.PASS)
                tests[2][1] = 1
            else:
                LOG.debug("Selective restore of full snapshot")
                raise Exception("Selective restore of full snapshot")

            # Fetch instance details after restore
            selective_vm_list = []
            selective_vm_list = self.get_restored_vm_list(restore_id)
            LOG.debug("Restored vm(selective) ID : " + str(selective_vm_list))

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


            try:
                if (deleted == 0):
                    self.delete_vm(vm_id)

                self.delete_vm(oneclick_vm_list[0])
                self.delete_vm(inplace_vm_list[0])
                self.delete_vm(selective_vm_list[0])
            except BaseException:
                pass



