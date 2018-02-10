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
from tempest import command_argument_string
from tempest.util import cli_parser
from tempest import upgrade_data_conf
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

            #Verify if global job scheduler setting is preserved
            self.scheduler = self.get_global_job_scheduler_status()
            LOG.debug("Expected scheduler status: " + str(tvaultconf.global_job_scheduler))
            LOG.debug("Actual scheduler status returned: " + str(self.scheduler))
            if(self.scheduler == tvaultconf.global_job_scheduler):
                reporting.add_test_step("Global job scheduler setting preserve", tvaultconf.PASS)
            else:
                reporting.add_test_step("Global job scheduler setting preserve", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            #Get list of workloads imported
            self.workloads = self.getWorkloadList()
            LOG.debug("Workload list after import: " + str(self.workloads))

            #Verify if workload created before upgrade is imported
            self.workload_id_before_upgrade = upgrade_data_conf.workload_id
            LOG.debug("Workload id before upgrade: " + str(self.workload_id_before_upgrade))
            if(str(self.workload_id_before_upgrade) in self.workloads):
                reporting.add_test_step("Verify imported workload", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify imported workload", tvaultconf.FAIL)
                raise Exception("Imported workload verification failed")

            #Verify workload member details of imported workload
            self.workload_instances_data = self.getWorkloadDetails(self.workload_id_before_upgrade)['instances']
            self.workload_members_after_upgrade = []
            for instance in self.workload_instances_data:
                self.workload_members_after_upgrade.append(instance['id'])
            LOG.debug("Workload members before upgrade: " + str(upgrade_data_conf.instance_id) + " ; and after upgrade: " + str(self.workload_members_after_upgrade))
            if(self.workload_members_after_upgrade.sort() == upgrade_data_conf.instance_id.sort()):
                reporting.add_test_step("Verify workload members after import", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify workload members after import", tvaultconf.FAIL)

            #Verify if workload scheduler settings are preserved
            self.scheduler_settings_before_upgrade = upgrade_data_conf.scheduler_settings
            self.scheduler_settings_after_upgrade = self.getSchedulerDetails(self.workload_id_before_upgrade)
            LOG.debug("Scheduler settings before upgrade: " + str(self.scheduler_settings_before_upgrade) + " ; and after upgrade: " + str(self.scheduler_settings_after_upgrade))
            for key in self.scheduler_settings_before_upgrade.keys():
                if(key == 'nextrun'):
                    pass
                else:
                    if(self.scheduler_settings_before_upgrade[key] == self.scheduler_settings_after_upgrade[key]):
                        reporting.add_test_step("Workload scheduler '" + str(key) + "' preserve", tvaultconf.PASS)
                    else:
                        reporting.add_test_step("Workload scheduler '" + str(key) + "' preserve", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)

            #Get list of snapshots imported
            self.snapshots = self.getSnapshotList()
            LOG.debug("Snapshot list after import: " + str(self.snapshots))

            #Verify if snapshots created before upgrade are imported
            self.snapshot_before_upgrade = upgrade_data_conf.full_snapshot_id
            LOG.debug("Snapshot before upgrade: " + str(self.snapshot_before_upgrade))
            if(str(self.snapshot_before_upgrade) in self.snapshots):
                reporting.add_test_step("Verify imported snapshots", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify imported snapshots", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            self.original_vm_id = upgrade_data_conf.instance_id[0]
            LOG.debug("Original VM ID: " + str(self.original_vm_id))
            self.original_vols = upgrade_data_conf.volume_ids
            LOG.debug("Original Volume IDs: " + str(self.original_vols))

            #Create instance details for restore.json
            self.instance_details = []
            self.vol_details = []
            temp_vol_data = { 'id': self.original_vols[0],
                              'availability_zone':CONF.volume.volume_availability_zone,
                              'new_volume_type':CONF.volume.volume_type
                            }
            self.vol_details.append(temp_vol_data)
            temp_instance_data = { 'id': self.original_vm_id,
                                   'include': True,
                                   'name': "tempest_test_vm_restored_"+ str(self.workload_id_before_upgrade),
                                   'vdisks': self.vol_details,
                                   'availability_zone': CONF.compute.vm_availability_zone
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
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                self.wait_for_workload_tobe_available(self.workload_id_before_upgrade)
                if(self.getRestoreStatus(self.workload_id_before_upgrade, self.snapshot_before_upgrade, self.selective_restore_id) == "available"):
                    reporting.add_test_step("Selective restore of imported snapshot", tvaultconf.PASS)
                else:
                    reporting.add_test_step("Selective restore of imported snapshot", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)

            self.selective_restored_vms = self.get_restored_vm_list(self.selective_restore_id)
            self.selective_restored_volumes = self.get_restored_volume_list(self.selective_restore_id)

            #Verify workload definition after selective restore
            self.workload_instances_after_selective_restore = self.getWorkloadDetails(self.workload_id_before_upgrade)['instances']
            self.workload_members_after_selective_restore = []
            for instance in self.workload_instances_after_selective_restore:
                self.workload_members_after_selective_restore.append(instance['id'])
            LOG.debug("Workload members before selective restore: " + str(upgrade_data_conf.instance_id) + " ; and after selective restore: " + str(self.workload_members_after_selective_restore))
            if(self.workload_members_after_selective_restore.sort() == upgrade_data_conf.instance_id.sort()):
                reporting.add_test_step("Verify workload members after selective restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify workload members after selective restore", tvaultconf.FAIL)

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
                raise Exception("One click restore failed")

            self.oneclick_restored_vms = self.get_restored_vm_list(self.oneclick_restore_id)
            self.oneclick_restored_volumes = self.get_restored_volume_list(self.oneclick_restore_id)

            #Verify workload definition after one click restore
            self.workload_instances_after_oneclick_restore = self.getWorkloadDetails(self.workload_id_before_upgrade)['instances']
            self.workload_members_after_oneclick_restore = []
            for instance in self.workload_instances_after_oneclick_restore:
                self.workload_members_after_oneclick_restore.append(instance['id'])
	    LOG.debug("Workload members after oneclick restore: " + str(self.workload_members_after_oneclick_restore))
            if(self.workload_members_after_oneclick_restore.sort() == self.oneclick_restored_vms.sort()):
                reporting.add_test_step("Verify workload members after oneclick restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify workload members after oneclick restore", tvaultconf.FAIL)

            #Trigger full snapshot of imported workload
            self.new_snapshot_id = self.workload_snapshot(self.workload_id_before_upgrade, is_full=True, snapshot_cleanup=False)
            LOG.debug("New full snapshot id of imported workload: " + str(self.new_snapshot_id))
            self.wait_for_workload_tobe_available(self.workload_id_before_upgrade)
            if(self.getSnapshotStatus(self.workload_id_before_upgrade, self.new_snapshot_id) == "available"):
                reporting.add_test_step("Create new snapshot of imported workload", tvaultconf.PASS)
            else:
                reporting.add_test_step("Create new snapshot of imported workload", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            #Cleanup
            #Delete selective restore
            self.restore_delete(self.workload_id_before_upgrade, self.snapshot_before_upgrade, self.selective_restore_id)
            self.delete_restored_vms(self.selective_restored_vms, self.selective_restored_volumes)

            #Delete one click restore
            self.restore_delete(self.workload_id_before_upgrade, self.snapshot_before_upgrade, self.oneclick_restore_id)
            self.delete_restored_vms(self.oneclick_restored_vms, self.oneclick_restored_volumes)

            #Delete new snapshot created
            self.snapshot_delete(self.workload_id_before_upgrade, self.new_snapshot_id)

            #Delete imported snapshot and workload
            self.snapshot_delete(self.workload_id_before_upgrade, self.snapshot_before_upgrade)
            self.workload_delete(self.workload_id_before_upgrade)
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
