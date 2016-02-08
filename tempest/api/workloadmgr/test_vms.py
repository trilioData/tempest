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
    workload_id = ''

    @classmethod
    def setup_clients(self):
        super(WorkloadsTest, self).setup_clients()
  
    @test.attr(type='smoke')
    @test.idempotent_id('3d64b5d3-b283-418c-82de-2b3394e57925')
    def test_1(self):
        self.total_vms=50
        self.volume_size=1
        self.workload_instances = []
        self.workload_volumes = []
        for vm in range(0,self.total_vms):
            vm_id = self.create_vm()
            self.workload_instances.append(vm_id)
            volume_id = self.create_volume(self.volume_size,tvaultconf.volume_type)
            self.workload_volumes.append(volume_id)
            self.attach_volume(volume_id, vm_id)

        self.workload_id = self.workload_create(self.workload_instances,tvaultconf.parallel)
        self.snapshot_id=self.workload_snapshot(self.workload_id, True)
        self.assertEqual(self.getSnapshotStatus(self.workload_id, self.snapshot_id), "available")
        self.workload_reset(self.workload_id)
        time.sleep(600)
        self.delete_vms(self.workload_instances)
        self.restore_id = self.snapshot_restore(self.workload_id, self.snapshot_id)
        self.assertEqual(self.getRestoreStatus(self.workload_id, self.snapshot_id, self.restore_id), "available")
