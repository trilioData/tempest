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
from tempest import tvaultconf
import json
import yaml
import sys
from tempest import api
from oslo_log import log as logging
from tempest.common import waiters
from tempest import tvaultconf
from tempest import reporting
import time
from tempest import command_argument_string
from tempest.util import cli_parser
from tempest.util import query_data
import collections

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
        reporting.add_test_script(str(__name__))

    @test.pre_req({'type': 'inplace'})
    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f522eada4c9')
    def test_tvault_inplace_cli_delete_vm(self):
        try:

            volumes = ["/dev/vdb", "/dev/vdc"]
            mount_points = ["mount_data_b", "mount_data_c"]

            # Fill some data on each of the volumes attached
            ssh = self.SshRemoteMachineConnectionWithRSAKey(
                str(self.floating_ips_list[0]))
            self.addCustomfilesOnLinuxVM(ssh, mount_points[0], 1)
            ssh.close()

            ssh = self.SshRemoteMachineConnectionWithRSAKey(
                str(self.floating_ips_list[1]))
            self.addCustomfilesOnLinuxVM(ssh, mount_points[0], 1)
            self.addCustomfilesOnLinuxVM(ssh, mount_points[1], 1)
            ssh.close()

            # Fill some more data on each volume attached
            def tree(): return collections.defaultdict(tree)
            self.md5sums_dir_before = tree()

            ssh = self.SshRemoteMachineConnectionWithRSAKey(
                str(self.floating_ips_list[0]))
            self.md5sums_dir_before[str(self.floating_ips_list[0])][str(
                mount_points[0])] = self.calculatemmd5checksum(ssh, mount_points[0])
            ssh.close()

            ssh = self.SshRemoteMachineConnectionWithRSAKey(
                str(self.floating_ips_list[1]))
            self.md5sums_dir_before[str(self.floating_ips_list[1])][str(
                mount_points[0])] = self.calculatemmd5checksum(ssh, mount_points[0])
            self.md5sums_dir_before[str(self.floating_ips_list[1])][str(
                mount_points[1])] = self.calculatemmd5checksum(ssh, mount_points[1])
            ssh.close()

            LOG.debug("md5sums_dir_before" + str(self.md5sums_dir_before))

            # delete vm and delete on volume
            self.delete_vm(self.workload_instances[0])
            self.delete_volume(self.volumes_list[1])

            # Create in-place restore with CLI command
            restore_command = command_argument_string.inplace_restore + \
                str(tvaultconf.restore_filename) + \
                " " + str(self.incr_snapshot_id)

            LOG.debug("inplace restore cli command: " + str(restore_command))
            # Restore.json with only volume 2 excluded
            restore_json = json.dumps({
                'openstack': {
                    'instances': [{
                        'restore_boot_disk': True,
                        'include': False,
                        'id': self.workload_instances[0],
                        'vdisks': []
                        },
                        {
                        'restore_boot_disk': True,
                        'include': True,
                        'id': self.workload_instances[1],
                        'vdisks': [{
                            'restore_cinder_volume': True,
                            'id': self.volumes_list[2],
                            'new_volume_type':CONF.volume.volume_type
                        }]
                        }],
                    'networks_mapping': {
                        'networks': []
                        }
                    },
                'restore_type': 'inplace',
                'type': 'openstack'
                })
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
            self.restore_id = query_data.get_snapshot_restore_id(
                self.incr_snapshot_id)
            self.wait_for_snapshot_tobe_available(
                self.workload_id, self.incr_snapshot_id)

            # get in-place restore status
            if(self.getRestoreStatus(self.workload_id, self.incr_snapshot_id, self.restore_id) == "available"):
                reporting.add_test_step("In-place restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("In-place restore", tvaultconf.FAIL)
                raise Exception("In-place restore failed")

            # mount volumes after restore
            ssh = self.SshRemoteMachineConnectionWithRSAKey(
                str(self.floating_ips_list[1]))
            self.execute_command_disk_mount(
                ssh, str(self.floating_ips_list[1]), volumes, mount_points)
            ssh.close()

            # calculate md5 after inplace restore
            def tree(): return collections.defaultdict(tree)
            md5_sum_after_in_place_restore = tree()

            ssh = self.SshRemoteMachineConnectionWithRSAKey(
                str(self.floating_ips_list[1]))
            md5_sum_after_in_place_restore[str(self.floating_ips_list[1])][str(
                mount_points[0])] = self.calculatemmd5checksum(ssh, mount_points[0])
            md5_sum_after_in_place_restore[str(self.floating_ips_list[1])][str(
                mount_points[1])] = self.calculatemmd5checksum(ssh, mount_points[1])
            ssh.close()

            LOG.debug("md5_sum_after_in_place_restore" +
                      str(md5_sum_after_in_place_restore))

            # md5 sum verification
            if self.md5sums_dir_before[str(self.floating_ips_list[1])][str(mount_points[0])] == md5_sum_after_in_place_restore[str(self.floating_ips_list[1])][str(mount_points[0])]:
                reporting.add_test_step(
                    "Md5 Verification for volume 1", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Md5 Verification for volume 1", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            if self.md5sums_dir_before[str(self.floating_ips_list[1])][str(mount_points[1])] != md5_sum_after_in_place_restore[str(self.floating_ips_list[1])][str(mount_points[1])]:
                reporting.add_test_step(
                    "Md5 Verification for volume 2", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Md5 Verification for volume 2", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # Delete restore for snapshot
            self.restored_volumes = self.get_restored_volume_list(
                self.restore_id)
            if tvaultconf.cleanup == True:
                self.restore_delete(
                    self.workload_id, self.incr_snapshot_id, self.restore_id)
                LOG.debug("Snapshot Restore deleted successfully")

                # Delete restored volumes and volume snapshots
                self.delete_volumes(self.restored_volumes)

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
