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

import sys
from tempest.api.workloadmgr import base
from tempest import config
from tempest import test
import json
import datetime
import time
from datetime import datetime, timedelta
from tempest import api
from oslo_log import log as logging
from tempest.common import waiters
from tempest import tvaultconf
import os
LOG = logging.getLogger(__name__)
CONF = config.CONF
sys.path.append(os.getcwd())


class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        cls.client = cls.os.wlm_client

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_create_workload(self):
        self.total_workloads = 1
        self.vms_per_workload = 1
        self.volume_size = 1
        self.workload_instances = []
        self.workload_volumes = []
        self.workloads = []
        self.date = time.strftime("%Y-%m-%d %H:%M:%S")

        # Scheduler start time will be 10 min after the workload create
        self.workload_start_date = datetime.strptime(
            self.date, "%Y-%m-%d %H:%M:%S") + timedelta(minutes=10)
        self.start_date = self.workload_start_date.strftime("%Y-%m-%d")
        self.start_time = self.workload_start_date.strftime("%H:%M:%S")
        self.enabled = True
        file = open("Tvault-1267.txt", "a")
        self.schedule = {"retention_policy_type": "Number of Snapshots to Keep", "enabled": self.enabled,
                         "start_date": self.start_date, "start_time": self.start_time, "interval": tvaultconf.interval, "retention_policy_value": 1}
        self.description = "Test Number of Snapshots to Keep"
        for vm in range(0, self.vms_per_workload):
            self.vm_id = self.create_vm(False)
            self.workload_instances.append(self.vm_id)
            self.volume_id = self.create_volume(
                self.volume_size, tvaultconf.volume_type, False)
            self.workload_volumes.append(self.volume_id)
            self.attach_volume(self.volume_id, self.vm_id,
                               attach_cleanup=False)
        self.workload_id = self.workload_create(
            self.workload_instances, tvaultconf.parallel, self.schedule, 'Workload-1', False, self.description)
        self.wait_for_workload_tobe_available(self.workload_id)
        self.assertEqual(self.getRetentionPolicyTypeStatus(
            self.workload_id), 'Number of Snapshots to Keep')
        self.assertEqual(
            self.getRetentionPolicyValueStatus(self.workload_id), 1)

        # Write data in file
        file.write('workload_id = ' + self.workload_id + '\n')
        file.write('volume_id = ' + self.volume_id + '\n')
        file.write('vm_id = ' + self.vm_id + '\n')
