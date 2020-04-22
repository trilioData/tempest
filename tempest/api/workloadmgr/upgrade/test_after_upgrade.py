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

    def _compare_global_jobscheduler(self):
        self.scheduler = self.get_global_job_scheduler_status()
        LOG.debug("Expected scheduler status: " +
                  str(tvaultconf.global_job_scheduler))
        LOG.debug("Actual scheduler status returned: " + str(self.scheduler))
        if(self.scheduler == tvaultconf.global_job_scheduler):
            return True
        else:
            return False

    def _compare_license(self):
        self.license_check_flag = True
        self.license_after_upgrade = self.get_license_list()
        LOG.debug("License imported on upgrade: " +
                  str(self.license_after_upgrade))
        LOG.debug("License before upgrade: " +
                  str(upgrade_data_conf.license_details))
        for key in upgrade_data_conf.license_details.keys():
            if self.license_after_upgrade:
                if(key == "metadata"):
                    for k in upgrade_data_conf.license_details[key][0].keys():
                        if(upgrade_data_conf.license_details[key][0][k] == self.license_after_upgrade[key][0][k]):
                            LOG.debug("License metadata '" +
                                      str(k) + "' imported correctly")
                        else:
                            self.license_check_flag = False
                            reporting.add_test_step(
                                "License metadata '" + str(k) + "' not imported correctly", tvaultconf.FAIL)
                            reporting.set_test_script_status(tvaultconf.FAIL)
                elif(self.license_after_upgrade[key] == upgrade_data_conf.license_details[key]):
                    LOG.debug("License data '" + str(key) +
                              "' imported correctly")
                else:
                    self.license_check_flag = False
                    reporting.add_test_step(
                        "License data '" + str(key) + "' not imported correctly", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                self.license_check_flag = False
                reporting.add_test_step(
                    "License not imported correctly", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            return self.license_check_flag

    def _compare_trust(self):
        self.trust_check_flag = True
        self.trust_after_upgrade = self.get_trust_list()
        LOG.debug("Trust imported on upgrade: " +
                  str(self.trust_after_upgrade))
        LOG.debug("Trust before upgrade: " +
                  str(upgrade_data_conf.trust_details))
        for i in range(0, len(upgrade_data_conf.trust_details)):
            for key in upgrade_data_conf.trust_details[i].keys():
                if self.trust_after_upgrade:
                    if(key == "metadata"):
                        for j in range(0, len(upgrade_data_conf.trust_details[i][key])):
                            for k in upgrade_data_conf.trust_details[i][key][j].keys():
                                if(upgrade_data_conf.trust_details[i][key][j][k] == self.trust_after_upgrade[i][key][j][k]):
                                    LOG.debug("Trust metadata '" +
                                              str(k) + "' imported correctly")
                                else:
                                    self.trust_check_flag = False
                                    reporting.add_test_step(
                                        "Trust metadata '" + str(k) + "' not imported correctly", tvaultconf.FAIL)
                                    reporting.set_test_script_status(
                                        tvaultconf.FAIL)
                    elif(upgrade_data_conf.trust_details[i][key] == self.trust_after_upgrade[i][key]):
                        LOG.debug("Trust data '" + str(key) +
                                  "' imported correctly")
                    else:
                        self.trust_check_flag = False
                        reporting.add_test_step(
                            "Trust data '" + str(key) + "' not imported correctly", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)
                else:
                    self.trust_check_flag = False
                    reporting.add_test_step(
                        "Trust not imported correctly", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
        return self.trust_check_flag

    def _compare_email_settings(self):
        self.email_check_flag = True
        self.settings_after_upgrade = self.get_settings_list()
        LOG.debug("Setting list after upgrade: " +
                  str(self.settings_after_upgrade))
        self.tmp_settings = upgrade_data_conf.settings_list
        self.tmp_settings.append(upgrade_data_conf.email_enabled_settings)
        self.settings_before_upgrade = {}
        for setting in self.tmp_settings:
            self.settings_before_upgrade[setting['name']] = setting['value']
        LOG.debug("Setting list before upgrade: " +
                  str(self.settings_before_upgrade))
        if self.settings_after_upgrade:
            for key in self.settings_before_upgrade.keys():
                if(str(self.settings_after_upgrade[key]) == str(self.settings_before_upgrade[key])):
                    LOG.debug("Email setting '" + str(key) + "' preserved")
                else:
                    self.email_check_flag = False
                    reporting.add_test_step(
                        "Email setting '" + str(key) + "' not preserve", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
        else:
            self.email_check_flag = False
            reporting.add_test_step(
                "Email settings not imported", tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        return self.email_check_flag

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_after_upgrade(self):
        try:
            # Import workloads using CLI command
            LOG.debug("Workload import CLI command started at: " +
                      str(datetime.datetime.now()))
            rc = cli_parser.cli_returncode(
                command_argument_string.workload_import)
            LOG.debug("Workload import CLI command ended at: " +
                      str(datetime.datetime.now()))
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-importworkloads command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-importworkloads command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            # Verify if global job scheduler setting is preserved
            if self._compare_global_jobscheduler():
                reporting.add_test_step(
                    "Global job scheduler setting preserve", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Global job scheduler setting preserve", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # Verify if license is imported correctly
            if self._compare_license():
                reporting.add_test_step(
                    "License details imported correctly", tvaultconf.PASS)

            # Verify if trust is imported correctly
            if self._compare_trust():
                reporting.add_test_step(
                    "Trust imported correctly", tvaultconf.PASS)

            # Verify if email settings are imported after upgrade
            if self._compare_email_settings():
                reporting.add_test_step(
                    "Email settings imported correctly", tvaultconf.PASS)

            # Get list of workloads imported
            self.workloads = self.getWorkloadList()
            LOG.debug("Workload list after import: " + str(self.workloads))

            # Fetch data from upgrade_data_conf
            self.data_before_upgrade = []
            self.data_before_upgrade.append({})
            self.data_before_upgrade[0]['workload_id'] = upgrade_data_conf.workload_id
            self.data_before_upgrade[0]['snapshot_id'] = upgrade_data_conf.full_snapshot_id
            self.data_before_upgrade[0]['instances'] = upgrade_data_conf.instance_id
            self.data_before_upgrade[0]['volumes'] = upgrade_data_conf.volume_ids
            self.data_before_upgrade[0]['scheduler_settings'] = upgrade_data_conf.scheduler_settings
            self.data_before_upgrade.append({})
            self.data_before_upgrade[1]['workload_id'] = upgrade_data_conf.workload_id_2
            self.data_before_upgrade[1]['snapshot_id'] = upgrade_data_conf.full_snapshot_id_2
            self.data_before_upgrade[1]['instances'] = upgrade_data_conf.instance_id_2
            self.data_before_upgrade[1]['volumes'] = upgrade_data_conf.volume_ids_2
            self.data_before_upgrade[1]['scheduler_settings'] = upgrade_data_conf.scheduler_settings_2

            # Verify if workloads created before upgrade are imported
            self.workloads_before_upgrade = []
            for i in range(0, len(self.data_before_upgrade)):
                self.workloads_before_upgrade.append(
                    self.data_before_upgrade[i]['workload_id'])
            LOG.debug("Workloads before upgrade: " +
                      str(self.workloads_before_upgrade))
            if(all(id in self.workloads for id in self.workloads_before_upgrade)):
                reporting.add_test_step(
                    "Verify imported workloads", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify imported workloads", tvaultconf.FAIL)
                raise Exception("Imported workload verification failed")

            # Verify workload member details of imported workload
            for i in range(0, len(self.workloads_before_upgrade)):
                self.workload_instances_data = self.get_workload_details(
                    self.workloads_before_upgrade[i])['instances']
                self.workload_members_after_upgrade = []
                for instance in self.workload_instances_data:
                    self.workload_members_after_upgrade.append(instance['id'])
                LOG.debug("Workload members before upgrade: " + str(upgrade_data_conf.instance_id) +
                          " ; and after upgrade: " + str(self.workload_members_after_upgrade))
                if(self.workload_members_after_upgrade.sort() == upgrade_data_conf.instance_id.sort()):
                    reporting.add_test_step(
                        "Verify workload members after import for workload " + str(i + 1), tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Verify workload members after import for workload " + str(i + 1), tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)

            # Verify if workload scheduler settings are preserved
            for i in range(0, len(self.workloads_before_upgrade)):
                self.scheduler_settings_check_flag = True
                self.scheduler_settings_before_upgrade = self.data_before_upgrade[
                    i]['scheduler_settings']
                self.scheduler_settings_after_upgrade = self.getSchedulerDetails(
                    self.data_before_upgrade[i]['workload_id'])
                LOG.debug("Scheduler settings before upgrade: " + str(self.scheduler_settings_before_upgrade) +
                          " ; and after upgrade: " + str(self.scheduler_settings_after_upgrade))
                for key in self.scheduler_settings_before_upgrade.keys():
                    if(key == 'nextrun'):
                        pass
                    else:
                        if(self.scheduler_settings_before_upgrade[key] == self.scheduler_settings_after_upgrade[key]):
                            LOG.debug("Workload scheduler '" + str(key) +
                                      "' preserved for workload " + str(i + 1))
                        else:
                            self.scheduler_settings_check_flag = False
                            reporting.add_test_step("Workload scheduler '" + str(
                                key) + "' not preserved for workload " + str(i + 1), tvaultconf.FAIL)
                            reporting.set_test_script_status(tvaultconf.FAIL)

                if self.scheduler_settings_check_flag:
                    reporting.add_test_step(
                        "Scheduler settings preserved for workload " + str(i + 1), tvaultconf.PASS)

            # Get list of snapshots imported
            self.snapshots = self.getSnapshotList()
            LOG.debug("Snapshot list after import: " + str(self.snapshots))

            # Verify if snapshots created before upgrade are imported
            self.snapshots_before_upgrade = []
            for i in range(0, len(self.data_before_upgrade)):
                self.snapshots_before_upgrade.append(
                    self.data_before_upgrade[i]['snapshot_id'])
            LOG.debug("Snapshots before upgrade: " +
                      str(self.snapshots_before_upgrade))
            if(all(id in self.snapshots for id in self.snapshots_before_upgrade)):
                reporting.add_test_step(
                    "Verify imported snapshots", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify imported snapshots", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            self.original_vm_id = upgrade_data_conf.instance_id[0]
            LOG.debug("Original VM ID: " + str(self.original_vm_id))
            self.original_vols = upgrade_data_conf.volume_ids
            LOG.debug("Original Volume IDs: " + str(self.original_vols))

            # Create instance details for restore.json
            self.instance_details = []
            self.vol_details = []
            temp_vol_data = {'id': self.original_vols[0],
                             'availability_zone': CONF.volume.volume_availability_zone,
                             'new_volume_type': CONF.volume.volume_type
                             }
            self.vol_details.append(temp_vol_data)
            temp_instance_data = {'id': self.original_vm_id,
                                  'include': True,
                                  'name': "tempest_test_vm_restored_" + str(self.data_before_upgrade[0]['workload_id']),
                                  'vdisks': self.vol_details,
                                  'availability_zone': CONF.compute.vm_availability_zone
                                  }
            self.instance_details.append(temp_instance_data)
            LOG.debug("Instance details for restore: " +
                      str(self.instance_details))

            # Create network details for restore.json
            self.network_details = []
            int_net_1_name = self.get_net_name(
                CONF.network.internal_network_id)
            LOG.debug("int_net_1_name" + str(int_net_1_name))
            int_net_1_subnets = self.get_subnet_id(
                CONF.network.internal_network_id)
            LOG.debug("int_net_1_subnet" + str(int_net_1_subnets))
            snapshot_network = {'name': int_net_1_name,
                                'id': CONF.network.internal_network_id,
                                'subnet': {'id': int_net_1_subnets}
                                }
            target_network = {'name': int_net_1_name,
                              'id': CONF.network.internal_network_id,
                              'subnet': {'id': int_net_1_subnets}
                              }
            self.network_details = [{'snapshot_network': snapshot_network,
                                     'target_network': target_network}]
            LOG.debug("Network details for restore: " +
                      str(self.network_details))

            # Trigger selective restore of imported snapshot of workload-1
            self.selective_restore_id = self.snapshot_selective_restore(
                self.data_before_upgrade[0]['workload_id'], self.data_before_upgrade[0]['snapshot_id'], instance_details=self.instance_details, network_details=self.network_details, restore_cleanup=False)
            LOG.debug("Selective Restore ID: " +
                      str(self.selective_restore_id))
            if(self.selective_restore_id == 0):
                reporting.add_test_step(
                    "Trigger selective restore of imported snapshot for workload-1", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                self.wait_for_workload_tobe_available(
                    self.data_before_upgrade[0]['workload_id'])
                if(self.getRestoreStatus(self.data_before_upgrade[0]['workload_id'], self.data_before_upgrade[0]['snapshot_id'], self.selective_restore_id) == "available"):
                    reporting.add_test_step(
                        "Selective restore of imported snapshot for workload-1", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Selective restore of imported snapshot for workload-1", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)

            self.selective_restored_vms = self.get_restored_vm_list(
                self.selective_restore_id)
            self.selective_restored_volumes = self.get_restored_volume_list(
                self.selective_restore_id)

            # Verify workload definition after selective restore
            self.workload_instances_after_selective_restore = self.get_workload_details(
                self.data_before_upgrade[0]['workload_id'])['instances']
            self.workload_members_after_selective_restore = []
            for instance in self.workload_instances_after_selective_restore:
                self.workload_members_after_selective_restore.append(
                    instance['id'])
            LOG.debug("Workload members before selective restore: " + str(upgrade_data_conf.instance_id) +
                      " ; and after selective restore: " + str(self.workload_members_after_selective_restore))
            if(self.workload_members_after_selective_restore.sort() == upgrade_data_conf.instance_id.sort()):
                reporting.add_test_step(
                    "Verify workload members after selective restore for workload-1", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload members after selective restore for workload-1", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # Delete original VM
            self.delete_vm(self.original_vm_id)

            # Trigger one click restore of imported snapshot of workload-1
            self.oneclick_restore_id = self.snapshot_restore(
                self.data_before_upgrade[0]['workload_id'], self.data_before_upgrade[0]['snapshot_id'], restore_cleanup=False)
            LOG.debug("Oneclick Restore ID: " + str(self.oneclick_restore_id))
            self.wait_for_workload_tobe_available(
                self.data_before_upgrade[0]['workload_id'])
            if(self.getRestoreStatus(self.data_before_upgrade[0]['workload_id'], self.data_before_upgrade[0]['snapshot_id'], self.oneclick_restore_id) == "available"):
                reporting.add_test_step(
                    "One click restore of imported snapshot for workload-1", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "One click restore of imported snapshot for workload-1", tvaultconf.FAIL)
                raise Exception("One click restore failed")

            self.oneclick_restored_vms = self.get_restored_vm_list(
                self.oneclick_restore_id)
            self.oneclick_restored_volumes = self.get_restored_volume_list(
                self.oneclick_restore_id)

            # Verify workload definition after one click restore
            self.workload_instances_after_oneclick_restore = self.get_workload_details(
                self.data_before_upgrade[0]['workload_id'])['instances']
            self.workload_members_after_oneclick_restore = []
            for instance in self.workload_instances_after_oneclick_restore:
                self.workload_members_after_oneclick_restore.append(
                    instance['id'])
            LOG.debug("Workload members after oneclick restore: " +
                      str(self.workload_members_after_oneclick_restore))
            if(self.workload_members_after_oneclick_restore.sort() == self.oneclick_restored_vms.sort()):
                reporting.add_test_step(
                    "Verify workload members after oneclick restore for workload-1", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify workload members after oneclick restore for workload-1", tvaultconf.FAIL)

            # Trigger full snapshot of imported workloads
            self.new_snapshots = []
            for i in range(0, len(self.workloads_before_upgrade)):
                self.new_snapshot_id = self.workload_snapshot(
                    self.data_before_upgrade[i]['workload_id'], is_full=True, snapshot_cleanup=False)
                LOG.debug("New full snapshot id of imported workload " +
                          str(i + 1) + ": " + str(self.new_snapshot_id))
                self.new_snapshots.append(self.new_snapshot_id)

            for i in range(0, len(self.new_snapshots)):
                self.wait_for_workload_tobe_available(
                    self.data_before_upgrade[i]['workload_id'])
                if(self.getSnapshotStatus(self.data_before_upgrade[i]['workload_id'], self.new_snapshots[i]) == "available"):
                    reporting.add_test_step(
                        "Create new snapshot of imported workload " + str(i + 1), tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Create new snapshot of imported workload " + str(i + 1), tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)

            # Cleanup
            # Delete selective restore
            self.restore_delete(
                self.data_before_upgrade[i]['workload_id'], self.data_before_upgrade[i]['snapshot_id'], self.selective_restore_id)
            self.delete_restored_vms(
                self.selective_restored_vms, self.selective_restored_volumes)

            # Delete one click restore
            self.restore_delete(
                self.data_before_upgrade[i]['workload_id'], self.data_before_upgrade[i]['snapshot_id'], self.oneclick_restore_id)
            self.delete_restored_vms(
                self.oneclick_restored_vms, self.oneclick_restored_volumes)

            # Delete new snapshots created
            for i in range(0, len(self.new_snapshots)):
                self.snapshot_delete(
                    self.data_before_upgrade[i]['workload_id'], self.new_snapshots[i])

            # Delete imported snapshots and workloads
            for i in range(0, len(self.workloads_before_upgrade)):
                self.snapshot_delete(
                    self.data_before_upgrade[i]['workload_id'], self.data_before_upgrade[i]['snapshot_id'])
                self.workload_delete(
                    self.data_before_upgrade[i]['workload_id'])

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
