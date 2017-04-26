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
from tempest import api
from oslo_log import log as logging
from tempest.common import waiters
from tempest import tvaultconf
import time
LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        cls.client = cls.os.wlm_client

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_data_integrity(self):
        self.total_workloads=1
        self.vms_per_workload=2
        self.volume_size=1
        self.workload_instances = []
        self.workload_volumes = []
        self.workloads = []
        self.full_snapshots = []
        self.md5sums_dir_before = {}
        self.md5sums_dir_after = {}
        self.incr_snapshots = []
        self.restores = []
        self.fingerprint = ""
        self.vm_details_list = []

        self.original_fingerprint = self.create_key_pair(tvaultconf.key_pair_name)
        for vm in range(0,self.vms_per_workload):
             vm_id = self.create_vm()
             self.workload_instances.append(vm_id)
             volume_id1 = self.create_volume(self.volume_size,tvaultconf.volume_type)
             volume_id2 = self.create_volume(self.volume_size,tvaultconf.volume_type)
             self.workload_volumes.append(volume_id1)
             self.workload_volumes.append(volume_id2)
             self.attach_volume(volume_id1, vm_id, device="/dev/vdb")
             self.attach_volume(volume_id2, vm_id,device="/dev/vdc")

        floating_ips_list = self.get_floating_ips()

        for i in range(len(self.workload_instances)):
            self.set_floating_ip((floating_ips_list[i].encode('ascii','ignore')), self.workload_instances[i])
            self.execute_command_disk_create(floating_ips_list[i])
            self.execute_command_disk_mount(floating_ips_list[i])

        # before restore
        self.vm_details_list = []
        for i in range(len(self.workload_instances)):
            self.vm_details_list.append(self.get_restored_vm_details(self.workload_instances[i]))

        LOG.debug("vm details list before backups" + str( self.vm_details_list))
        self.md5sums_dir_before = self.data_populate_before_backup(self.workload_instances, floating_ips_list, 5)

        # create workload, take backup
        self.workload_id=self.workload_create(self.workload_instances,tvaultconf.parallel)
        self.snapshot_id=self.workload_snapshot(self.workload_id, True)
        self.wait_for_workload_tobe_available(self.workload_id)
        self.assertEqual(self.getSnapshotStatus(self.workload_id, self.snapshot_id), "available")
	self.workload_reset(self.workload_id)
        time.sleep(40)
        self.delete_vms(self.workload_instances)
        self.restore_id=self.snapshot_restore(self.workload_id, self.snapshot_id)
        self.wait_for_snapshot_tobe_available(self.workload_id, self.snapshot_id)
        self.assertEqual(self.getRestoreStatus(self.workload_id, self.snapshot_id, self.restore_id), "available","Workload_id: "+self.workload_id+" Snapshot_id: "+self.snapshot_id+" Restore id: "+self.restore_id)

        # after restore
        # verification
        # get restored vms list
        # self.get_restored_vm_details(self.restore_id)
        self.vm_list = []
        # restored_vm_details = ""
        self.restored_vm_details_list = []
        self.vm_list  =  self.get_restored_vm_list(self.restore_id)
        LOG.debug("Restored vms : " + str (self.vm_list))
        floating_ips_list_after_restore = []
        for i in range(len(self.vm_list)):
            self.restored_vm_details_list.append(self.get_restored_vm_details(self.vm_list[i]))

        LOG.debug("vm details list after restore" + str( self.restored_vm_details_list))
        for i in range(len(self.restored_vm_details_list)):
            floating_ips_list_after_restore.append(self.restored_vm_details_list[i]['server']['addresses']['int-net'][1]['addr'])

        self.md5sums_dir_after = self.calculate_md5_after_restore(self.vm_list, floating_ips_list_after_restore)
    #
    #     # verification one-click restore
        for i in range(len(self.workload_instances)):
            self.assertTrue(self.md5sums_dir_before[str(floating_ips_list_after_restore[i])]==self.md5sums_dir_after[str(floating_ips_list_after_restore[i])], "md5sum verification unsuccessful for ip" + str(floating_ips_list_after_restore[i]))
    #
    #     # incremental change
        self.md5sums_dir_before = self.data_populate_before_backup(self.vm_list, floating_ips_list_after_restore, 7)
    #
    #     # incremental snapshot backup
        self.snapshot_id=self.workload_snapshot(self.workload_id, False)
        self.wait_for_workload_tobe_available(self.workload_id)
        self.assertEqual(self.getSnapshotStatus(self.workload_id, self.snapshot_id), "available")
	self.workload_reset(self.workload_id)
        time.sleep(40)
        self.delete_vms(self.workload_instances)
        self.restore_id=self.snapshot_selective_restore(self.workload_id, self.snapshot_id)
        self.wait_for_snapshot_tobe_available(self.workload_id, self.snapshot_id)
        self.assertEqual(self.getRestoreStatus(self.workload_id, self.snapshot_id, self.restore_id), "available","Workload_id: "+self.workload_id+" Snapshot_id: "+self.snapshot_id+" Restore id: "+self.restore_id)

        # after selective restore_id and incremental change
        # after restore
        self.vm_list = []
        # restored_vm_details = ""
        self.restored_vm_details_list = []
        self.vm_list  =  self.get_restored_vm_list(self.restore_id)
        LOG.debug("Restored vms : " + str (self.vm_list))
        floating_ips_list_after_restore = []
        for i in range(len(self.vm_list)):
            self.restored_vm_details_list.append(self.get_restored_vm_details(self.vm_list[i]))
        LOG.debug("Restored vm detaild list after incremental change " + str(self.restored_vm_details_list))

        for i in range(len(self.restored_vm_details_list)):
            floating_ips_list_after_restore.append(self.restored_vm_details_list[i]['server']['addresses']['int-net'][1]['addr'])
        self.md5sums_dir_after = self.calculate_md5_after_restore(self.vm_list, floating_ips_list_after_restore)

        # verification selective restore incremental change
        for i in range(len(self.workload_instances)):
            self.assertTrue(self.md5sums_dir_before[str(floating_ips_list_after_restore[i])]==self.md5sums_dir_after[str(floating_ips_list_after_restore[i])], "md5sum verification unsuccessful for ip" + str(floating_ips_list_after_restore[i]))
