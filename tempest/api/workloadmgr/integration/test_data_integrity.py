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
        self.volume_size=2
        self.workload_instances = []
        self.workload_volumes = []
        self.workloads = []
        self.full_snapshots = []
        self.md5sums_dir_before = {}
        self.md5sums_dir_after = {}
        self.incr_snapshots = []
        self.restores = []
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

        # before restore
        for i in range(len(self.workload_instances)):
            self.md5sums = ""
            LOG.debug("setting floating ip" + (floating_ips_list[i].encode('ascii','ignore')))

            self.set_floating_ip((floating_ips_list[i].encode('ascii','ignore')), self.workload_instances[i])
            self.execute_command_disk_create(floating_ips_list[i])
            self.execute_command_disk_mount(floating_ips_list[i])

            self.addCustomSizedfilesOnLinux(floating_ips_list[i],"mount_data_b" +"/",2,1048576, 100)
            self.md5sums +=(self.calculatemmd5checksum(floating_ips_list[i],"mount_data_b" +"/"))

            self.addCustomSizedfilesOnLinux(floating_ips_list[i],"mount_data_c" +"/",2,1048576, 100)
            self.md5sums+=(self.calculatemmd5checksum(floating_ips_list[i],"mount_data_c" +"/"))

            self.addCustomSizedfilesOnLinux(floating_ips_list[i],"/root" +"/",2,1048576, 100)
            self.md5sums+=(self.calculatemmd5checksum(floating_ips_list[i],"/root" +"/"))

            self.md5sums_dir_before[str(floating_ips_list[i])] = self.md5sums

            LOG.debug("before backup md5sum for " + floating_ips_list[i].encode('ascii','ignore') + " " +str(self.md5sums))

        LOG.debug("before backup md5sum : " + str(self.md5sums_dir_before))


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
        self.get_restored_vm_details(self.restore_id)

        for i in range(len(self.workload_instances)):
            self.md5sums = ""

            self.execute_command_disk_mount(floating_ips_list[i])

            self.md5sums+=(self.calculatemmd5checksum(floating_ips_list[i],"mount_data_b" +"/"))

            self.md5sums+=(self.calculatemmd5checksum(floating_ips_list[i],"mount_data_c" +"/"))

            self.md5sums+=(self.calculatemmd5checksum(floating_ips_list[i],"/root" +"/"))

            self.md5sums_dir_after[str(floating_ips_list[i])] = self.md5sums

            LOG.debug("after md5sum for " + floating_ips_list[i].encode('ascii','ignore') + " " +str(self.md5sums))

        LOG.debug("after md5sum : " + str(self.md5sums_dir_after))

        # verification one-click restore
        for i in range(len(self.workload_instances)):
            self.assertTrue(self.md5sums_dir_before[str(floating_ips_list[i])]==self.md5sums_dir_after[str(floating_ips_list[i])], "md5sum verification unsuccessful for ip" + str(floating_ips_list[i]))

        # incremental change
        for i in range(len(self.workload_instances)):
            self.md5sums = ""
            self.addCustomSizedfilesOnLinux(floating_ips_list[i],"mount_data_b" +"/",2,1048576, 100)
            self.md5sums+=(self.calculatemmd5checksum(floating_ips_list[i],"mount_data_b" +"/"))

            self.addCustomSizedfilesOnLinux(floating_ips_list[i],"mount_data_c" +"/",2,1048576, 100)
            self.md5sums+=(self.calculatemmd5checksum(floating_ips_list[i],"mount_data_c" +"/"))

            self.addCustomSizedfilesOnLinux(floating_ips_list[i],"/root" +"/",2,1048576, 100)
            self.md5sums+=(self.calculatemmd5checksum(floating_ips_list[i],"/root" +"/"))

            self.md5sums_dir_before[str(floating_ips_list[i])] = self.md5sums

            LOG.debug("before backup md5sum for incremental change" + floating_ips_list[i].encode('ascii','ignore') + " " +str(self.md5sums))

        LOG.debug("before backup md5sum incremental change: " + str(self.md5sums_dir_before))

        # incremental snapshot backup
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
        for i in range(len(self.workload_instances)):
            self.md5sums = ""

            self.execute_command_disk_mount(floating_ips_list[i])

            self.md5sums+=(self.calculatemmd5checksum(floating_ips_list[i],"mount_data_b" +"/"))

            self.md5sums+=(self.calculatemmd5checksum(floating_ips_list[i],"mount_data_c" +"/"))

            self.md5sums+=(self.calculatemmd5checksum(floating_ips_list[i],"/root" +"/"))

            self.md5sums_dir_after[str(floating_ips_list[i])] = self.md5sums

            LOG.debug("after md5sum for incremental change" + floating_ips_list[i].encode('ascii','ignore') + " " +str(self.md5sums))

        LOG.debug("after md5sum incremental change: " + str(self.md5sums_dir_after))

        # verification selective restore incremental change
        for i in range(len(self.workload_instances)):
            self.assertTrue(self.md5sums_dir_before[str(floating_ips_list[i])]==self.md5sums_dir_after[str(floating_ips_list[i])], "md5sum verification unsuccessful for ip" + str(floating_ips_list[i]))
