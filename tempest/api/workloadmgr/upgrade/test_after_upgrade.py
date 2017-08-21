# Copyright 2014 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from tempest.api.workloadmgr import base
from tempest import config
from tempest import test
import json
import sys
import datetime
from tempest import api
from oslo_log import log as logging
from tempest.common import waiters
from tempest import tvaultconf
from tempest.api.workloadmgr.cli.config import command_argument_string
from tempest.api.workloadmgr.cli.util import cli_parser
from tempest import reporting

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
	reporting.add_test_script(str(__name__))

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_after_upgrade(self):
	try:
	    #Import workloads using CLI command
	    LOG.debug("Workload import CLI command started at: " + str(datetime.datetime.now()))
            rc = cli_parser.cli_returncode(command_argument_string.workload_import)
	    LOG.debug("Workload import CLI command ended at: " + str(datetime.datetime.now()))
            if rc != 0:
                reporting.add_test_step("Execute workload-importworkloads command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step("Execute workload-importworkloads command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

	    #Get list of workloads imported
	    self.workloads = self.getWorkloadList()
	    LOG.debug("Workload list after import: " + str(self.workloads))

	    #Verify if workload created before upgrade is imported
	    self.workload_id_before_upgrade = self.read_upgrade_data("workload_id")
	    LOG.debug("Workload id before upgrade: " + str(self.workload_id_before_upgrade))
	    if(str(self.workload_id_before_upgrade) in self.workloads):
	        reporting.add_test_step("Verify imported workload", tvaultconf.PASS)
            else:
	        reporting.add_test_step("Verify imported workload", tvaultconf.FAIL)
	        raise Exception("Imported workload verification failed")

	    #Get list of snapshots imported
	    self.snapshots = self.getSnapshotList()
	    LOG.debug("Snapshot list after import: " + str(self.snapshots))

	    #Verify if snapshots created before upgrade are imported
	    self.snapshot_before_upgrade = self.read_upgrade_data("full_snapshot_id")
	    LOG.debug("Snapshot before upgrade: " + str(self.snapshot_before_upgrade))
	    if(str(self.snapshot_before_upgrade) in self.snapshots):
	        reporting.add_test_step("Verify imported snapshots", tvaultconf.PASS)
	    else:
	        reporting.add_test_step("Verify imported snapshots", tvaultconf.FAIL)

	    self.original_vm_id = self.read_upgrade_data("instance_id")
            LOG.debug("Original VM ID: " + str(self.original_vm_id))
	
	    #Create instance details for restore.json
	    self.instance_details = []
            temp_instance_data = { 'id': self.original_vm_id,
                                   'include': True,
                                   'restore_boot_disk': True,
                                   'name': "tempest_test_vm_restored_"+ str(self.workload_id_before_upgrade),
                                   'vdisks':[]
                                 }
            self.instance_details.append(temp_instance_data)
            LOG.debug("Instance details for restore: " + str(self.instance_details))

            #Create network details for restore.json
	    self.network_details = []
	    int_net_1_name = self.get_net_name(CONF.network.internal_network_id)
            LOG.debug("int_net_1_name" + str(int_net_1_name))
            int_net_1_subnets = self.get_subnet_id(CONF.network.internal_network_id)
            LOG.debug("int_net_1_subnet" + str(int_net_1_subnets))
            snapshot_network = { 'name': int_net_1_name,
                                 'id': CONF.network.internal_network_id,
                                 'subnet': { 'id': int_net_1_subnets }
                               }
            target_network = { 'name': int_net_1_name,
                               'id': CONF.network.internal_network_id,
                               'subnet': { 'id': int_net_1_subnets }
                             }
            self.network_details = [ { 'snapshot_network': snapshot_network,
                                       'target_network': target_network } ]
            LOG.debug("Network details for restore: " + str(self.network_details))

 	    #Trigger selective restore of imported snapshot
	    self.selective_restore_id = self.snapshot_selective_restore(self.workload_id_before_upgrade, self.snapshot_before_upgrade, instance_details=self.instance_details, network_details=self.network_details, restore_cleanup=False)
	    LOG.debug("Selective Restore ID: " + str(self.selective_restore_id))
	    if(self.selective_restore_id == 0):
	        reporting.add_test_step("Trigger selective restore of imported snapshot", tvaultconf.FAIL)
	    else:
	        self.wait_for_workload_tobe_available(self.workload_id_before_upgrade)
	        if(self.getRestoreStatus(self.workload_id_before_upgrade, self.snapshot_before_upgrade, self.selective_restore_id) == "available"):
                    reporting.add_test_step("Selective restore of imported snapshot", tvaultconf.PASS)
                else:
                    reporting.add_test_step("Selective restore of imported snapshot", tvaultconf.FAIL)

	    #Delete original VM
	    self.delete_vm(self.original_vm_id)

	    #Trigger one click restore of imported snapshot
	    self.oneclick_restore_id = self.snapshot_restore(self.workload_id_before_upgrade, self.snapshot_before_upgrade, restore_cleanup=False)
	    LOG.debug("Oneclick Restore ID: " + str(self.oneclick_restore_id))
	    self.wait_for_workload_tobe_available(self.workload_id_before_upgrade)
 	    if(self.getRestoreStatus(self.workload_id_before_upgrade, self.snapshot_before_upgrade, self.oneclick_restore_id) == "available"):
	        reporting.add_test_step("One click restore of imported snapshot", tvaultconf.PASS)
	    else:
	        reporting.add_test_step("One click restore of imported snapshot", tvaultconf.FAIL)

	    #Trigger full snapshot of imported workload
	    self.new_snapshot_id = self.workload_snapshot(self.workload_id_before_upgrade, is_full=True, snapshot_cleanup=False)
	    LOG.debug("New full snapshot id of imported workload: " + str(self.new_snapshot_id))
	    self.wait_for_workload_tobe_available(self.workload_id_before_upgrade)
            if(self.getSnapshotStatus(self.workload_id_before_upgrade, self.new_snapshot_id) == "available"):
                reporting.add_test_step("Create new snapshot of imported workload", tvaultconf.PASS)
            else:
                reporting.add_test_step("Create new snapshot of imported workload", tvaultconf.FAIL)

	    #Cleanup
	    #Delete selective restore
	    self.restored_vms = self.get_restored_vm_list(self.selective_restore_id)
            self.restored_volumes = self.get_restored_volume_list(self.selective_restore_id)
            self.restore_delete(self.workload_id_before_upgrade, self.snapshot_before_upgrade, self.selective_restore_id)
            self.delete_restored_vms(self.restored_vms, self.restored_volumes)

	    #Delete one click restore
	    self.restored_vms = self.get_restored_vm_list(self.oneclick_restore_id)
            self.restored_volumes = self.get_restored_volume_list(self.oneclick_restore_id)
            self.restore_delete(self.workload_id_before_upgrade, self.snapshot_before_upgrade, self.oneclick_restore_id)
            self.delete_restored_vms(self.restored_vms, self.restored_volumes)

	    #Delete new snapshot created
	    self.snapshot_delete(self.workload_id_before_upgrade, self.new_snapshot_id)

	    #Delete imported snapshot and workload
	    self.snapshot_delete(self.workload_id_before_upgrade, self.snapshot_before_upgrade)
	    self.workload_delete(self.workload_id_before_upgrade)
	    reporting.test_case_to_write(tvaultconf.PASS)

	except Exception as e:
	    LOG.error("Exception: " + str(e))
	    reporting.test_case_to_write(tvaultconf.FAIL)
