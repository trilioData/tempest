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

import collections

from oslo_log import log as logging

from tempest import config
from tempest import reporting
from tempest import test
from tempest import tvaultconf
from tempest.api.workloadmgr import base
from tempest.lib import decorators

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        reporting.add_test_script(str(__name__))

    @test.pre_req({'type': 'bootfrom_image_with_floating_ips'})
    @decorators.attr(type='workloadmgr_api')
    def test_selectiverestore_defaultvalues(self):
        try:
            if self.exception != "":
                LOG.debug("pre req failed")
                reporting.add_test_step(str(self.exception), tvaultconf.FAIL)
                raise Exception(str(self.exception))
            LOG.debug("pre req completed")

            volumes = tvaultconf.volumes_parts
            mount_points = ["mount_data_b", "mount_data_c"]

            int_net_1_name = self.get_net_name(
                CONF.network.internal_network_id)
            LOG.debug("int_net_1_name" + str(int_net_1_name))
            int_net_1_subnets = self.get_subnet_id(
                CONF.network.internal_network_id)
            LOG.debug("int_net_1_subnet" + str(int_net_1_subnets))

            vdisks_data = []
            for vol in self.workload_volumes:
                vdisks_data.append(
                        { 'id': vol,
                          'availability_zone': CONF.volume.volume_availability_zone,
                          'new_volume_type': CONF.volume.volume_type})

            # Create instance details for restore.json
            for i in range(len(self.workload_instances)):
                vm_name = "tempest_test_vm_" + str(i + 1) + "_restored"
                temp_instance_data = {'id': self.workload_instances[i],
                                      'include': True,
                                      'restore_boot_disk': True,
                                      'name': vm_name,
                                      'vdisks': vdisks_data
                                      }
                self.instance_details.append(temp_instance_data)
            LOG.debug("Instance details for restore: " +
                      str(self.instance_details))

            # Create network details for restore.json
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

            # Fill some more data on each volume attached
            def tree(): return collections.defaultdict(tree)
            self.md5sums_dir_before = tree()
            for floating_ip in self.floating_ips_list:
                for mount_point in mount_points:
                    ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        str(floating_ip))
                    self.addCustomfilesOnLinuxVM(ssh, mount_point, 5)
                    ssh.close()
                for mount_point in mount_points:
                    ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        str(floating_ip))
                    self.md5sums_dir_before[str(floating_ip)][str(
                        mount_point)] = self.calculatemmd5checksum(ssh, mount_point)
                    ssh.close()

            LOG.debug("md5sums_dir_before" + str(self.md5sums_dir_before))

            # Trigger selective restore
            self.restore_id = self.snapshot_selective_restore(
                self.workload_id,
                self.snapshot_id,
                restore_name=tvaultconf.restore_name,
                instance_details=self.instance_details,
                network_details=self.network_details)
            self.wait_for_snapshot_tobe_available(
                self.workload_id, self.snapshot_id)
            if(self.getRestoreStatus(self.workload_id, self.snapshot_id, self.restore_id) == "available"):
                reporting.add_test_step("Selective restore", tvaultconf.PASS)
            else:
                restore_error = self.getRestoreDetails(self.restore_id)['restore']['error_msg']
                error_msg = f"Selective restore failed with error {restore_error}"
                reporting.add_test_step(error_msg, tvaultconf.FAIL)
                raise Exception("Selective restore failed")

            # Fetch instance details after restore
            self.restored_vm_details_list = []
            self.vm_list = self.get_restored_vm_list(self.restore_id)
            LOG.debug("Restored vms : " + str(self.vm_list))

            for id in range(len(self.vm_list)):
                self.restored_vm_details_list.append(
                    self.get_vm_details(self.vm_list[id]))
            LOG.debug("Restored vm details list: " +
                      str(self.restored_vm_details_list))

            self.vms_details_after_restore = self.get_vms_details_list(
                self.restored_vm_details_list)
            LOG.debug("VM details after restore: " +
                      str(self.vms_details_after_restore))

            # Compare the data before and after restore
            for i in range(len(self.vms_details_after_restore)):
                if(self.vms_details_after_restore[i]['network_name'] == int_net_1_name):
                    reporting.add_test_step(
                        "Network verification for instance-" + str(i + 1), tvaultconf.PASS)
                else:
                    LOG.error("Expected network: " + str(int_net_1_name))
                    LOG.error("Restored network: " +
                              str(self.vms_details_after_restore[i]['network_name']))
                    reporting.add_test_step(
                        "Network verification for instance-" + str(i + 1), tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
                if(self.get_key_pair_details(self.vms_details_after_restore[i]['keypair']) == self.original_fingerprint):
                    reporting.add_test_step(
                        "Keypair verification for instance-" + str(i + 1), tvaultconf.PASS)
                else:
                    LOG.error("Original keypair details: " +
                              str(self.original_fingerprint))
                    LOG.error(
                        "Restored keypair details: " + str(
                            self.get_key_pair_details(
                                self.vms_details_after_restore[i]['keypair'])))
                    reporting.add_test_step(
                        "Keypair verification for instance-" + str(i + 1), tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
                if(self.get_flavor_details(self.vms_details_after_restore[i]['flavor_id']) == self.original_flavor_conf):
                    reporting.add_test_step(
                        "Flavor verification for instance-" + str(i + 1), tvaultconf.PASS)
                else:
                    LOG.error("Original flavor details: " +
                              str(self.original_flavor_conf))
                    LOG.error(
                        "Restored flavor details: " + str(
                            self.get_flavor_details(
                                self.vms_details_after_restore[i]['flavor_id'])))
                    reporting.add_test_step(
                        "Flavor verification for instance-" + str(i + 1), tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)

            # Assign floating ips to restored vms
            self.new_floating_ips_list = self.get_floating_ips()
            self.restored_vm_floating_ips = []
            if (len(self.new_floating_ips_list) > 0):
                for i in range(len(self.vms_details_after_restore)):
                    self.set_floating_ip(self.new_floating_ips_list[i], 
                            self.vms_details_after_restore[i]['id'])
                    self.restored_vm_floating_ips.append(self.new_floating_ips_list[i])
            else:
                raise Exception("Floating ips unavailable to be assigned to restored instances")

            # calculate md5sum after restore
            def tree(): return collections.defaultdict(tree)
            md5_sum_after_selective_restore = tree()
            for floating_ip in self.restored_vm_floating_ips:
                for mount_point in mount_points:
                    ssh = self.SshRemoteMachineConnectionWithRSAKey(
                        str(floating_ip))
                    md5_sum_after_selective_restore[str(floating_ip)][str(
                        mount_point)] = self.calculatemmd5checksum(ssh, mount_point)
                    ssh.close()
            LOG.debug("md5_sum_after_selective_restore" +
                      str(md5_sum_after_selective_restore))

            # md5sum verification
            if(self.md5sums_dir_before == md5_sum_after_selective_restore):
                reporting.add_test_step("Md5 Verification", tvaultconf.PASS)
            else:
                reporting.set_test_script_status(tvaultconf.FAIL)
                reporting.add_test_step("Md5 Verification", tvaultconf.FAIL)

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
