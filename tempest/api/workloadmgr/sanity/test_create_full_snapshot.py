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
from tempest import tvaultconf, reporting

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
    def test_create_full_snapshot(self):
        self.total_workloads=1
        self.vms_per_workload=1
        self.volume_size=1
        self.workload_instances = []
        self.workload_volumes = []
        self.workloads = []
        self.full_snapshots = []
        for vm in range(0,self.vms_per_workload):
             vm_id = self.create_vm()
             self.workload_instances.append(vm_id)
             volume_id1 = self.create_volume()
             volume_id2 = self.create_volume()
             self.workload_volumes.append(volume_id1)
             self.workload_volumes.append(volume_id2)
             self.attach_volume(volume_id1, vm_id, device="/dev/vdb")
             self.attach_volume(volume_id2, vm_id,device="/dev/vdc")

	#Create workload
        self.workload_id=self.workload_create(self.workload_instances,tvaultconf.parallel, workload_cleanup=False)
	self.wait_for_workload_tobe_available(self.workload_id)
        if(self.getWorkloadStatus(self.workload_id) == "available"):
	     reporting.add_sanity_results("Create_Workload", tvaultconf.PASS)
	else:
	     reporting.add_sanity_results("Create_Workload", tvaultconf.FAIL)
	     raise Exception("Workload creation failed")
	self.workload_status = self.getWorkloadStatus(self.workload_id)

	#Create full snapshot
        self.snapshot_id=self.workload_snapshot(self.workload_id, True, snapshot_cleanup=False)
	self.wait_for_workload_tobe_available(self.workload_id)
        if(self.getSnapshotStatus(self.workload_id, self.snapshot_id) == "available"):
	     reporting.add_sanity_results("Create_Snapshot", tvaultconf.PASS)
	else:
	     reporting.add_sanity_results("Create_Snapshot", tvaultconf.FAIL)
	     raise Exception("Snapshot creation failed")

	#Delete snapshot
	resp = self.snapshot_delete(self.workload_id, self.snapshot_id)
	if resp:
             reporting.add_sanity_results("Delete_Snapshot", tvaultconf.PASS)
        else:
             reporting.add_sanity_results("Delete_Snapshot", tvaultconf.FAIL)
	     raise Exception("Snapshot deletion failed")	

	#Delete workload
	resp = self.workload_delete(self.workload_id)
	if resp:
	     reporting.add_sanity_results("Delete_Workload", tvaultconf.PASS)
	else:
	     reporting.add_sanity_results("Delete_Workload", tvaultconf.FAIL)
	     raise Exception("Workload deletion failed")

