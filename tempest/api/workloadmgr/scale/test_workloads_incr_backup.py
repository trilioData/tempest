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

import time

from oslo_log import log as logging

from tempest import config
from tempest import tvaultconf
from tempest.api.workloadmgr import base
from tempest.lib import decorators

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']
    workload_id = ''

    @classmethod
    def setup_clients(self):
        super(WorkloadsTest, self).setup_clients()

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('3d64b5d3-b283-418c-82de-2b3394e57925')
    @decorators.attr(type='workloadmgr_api')
    def test_1(self):
        self.total_workloads = 20
        self.vms_per_workload = 2
        self.volume_size = 1
        self.workload_instances = []
        self.workload_volumes = []
        self.workloads = []
        self.full_snapshots = []
        self.incr_snapshots = []
        self.restores = []
        for workload in range(0, self.total_workloads):
            workload_instances = []
            workload_volumes = []
            for vm in range(0, self.vms_per_workload):
                vm_id = self.create_vm()
                workload_instances.append(vm_id)
                self.workload_instances.append(vm_id)
                volume_id = self.create_volume()
                workload_volumes.append(volume_id)
                self.attach_volume(volume_id, vm_id)

            self.workload_id = self.workload_create(
                workload_instances, tvaultconf.parallel)
            self.workloads.append(self.workload_id)

        for workload in range(0, self.total_workloads):
            self.full_snapshots.append(
                self.workload_snapshot(self.workloads[workload], True))

        for workload in range(0, self.total_workloads):
            self.wait_for_workload_tobe_available(self.workloads[workload])
            self.assertEqual(
                self.getSnapshotStatus(
                    self.workloads[workload],
                    self.full_snapshots[workload]),
                "available")
            self.incr_snapshots.append(
                self.workload_snapshot(self.workloads[workload], False))

        for workload in range(0, self.total_workloads):
            self.wait_for_workload_tobe_available(self.workloads[workload])
            self.assertEqual(
                self.getSnapshotStatus(
                    self.workloads[workload],
                    self.incr_snapshots[workload]),
                "available",
                "Workload_id: " +
                self.workloads[workload] +
                " Snapshot_id: " +
                self.incr_snapshots[workload])
            self.workload_reset(self.workload_id)

        time.sleep(400)
        self.delete_vms(self.workload_instances)
        for workload in range(0, self.total_workloads):
            self.restores.append(self.snapshot_restore(
                self.workloads[workload], self.incr_snapshots[workload]))
        for workload in range(0, self.total_workloads):
            self.wait_for_snapshot_tobe_available(
                self.workloads[workload], self.incr_snapshots[workload])
            self.assertEqual(
                self.getRestoreStatus(
                    self.workloads[workload],
                    self.incr_snapshots[workload],
                    self.restores[workload]),
                "available",
                "Workload_id: " +
                self.workloads[workload] +
                " Snapshot_id: " +
                self.incr_snapshots[workload] +
                " Restore id: " +
                self.restores[workload])
