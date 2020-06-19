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
import apscheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from tempest.api.workloadmgr import base
from tempest import config
from tempest.lib import decorators
import json
import sys
import time
import os
from datetime import datetime, timedelta
from tempest import api
from oslo_log import log as logging
from tempest.common import waiters
from tempest import tvaultconf
sys.path.append(os.getcwd())
LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_create_workload(self):
        self.total_workloads = 1
        self.vms_per_workload = 1
        self.volume_size = 1
        self.workload_instances = []
        self.workload_volumes = []
        self.workloads = []
        self.full_snapshots = []
        self.incr_snapshots = []
        self.restores = []
        self.start_date = time.strftime("%x")
        self.start_time = time.strftime("%X")
        date = time.strftime("%Y-%m-%d %H:%M:%S")
        tvaultconf.count = 0
        self.enabled = True
        self.schedule = {
            "interval": tvaultconf.interval,
            "enabled": self.enabled,
            "start_date": self.start_date,
            "start_time": self.start_time}
        for vm in range(0, self.vms_per_workload):
            vm_id = self.create_vm()
            self.workload_instances.append(vm_id)
            volume_id1 = self.create_volume(
                self.volume_size, tvaultconf.volume_type)
            volume_id2 = self.create_volume(
                self.volume_size, tvaultconf.volume_type)
            self.workload_volumes.append(volume_id1)
            self.workload_volumes.append(volume_id2)
            self.attach_volume(volume_id1, vm_id, device="/dev/vdb")
            self.attach_volume(volume_id2, vm_id, device="/dev/vdc")

        self.workload_id = self.workload_create(
            self.workload_instances,
            tvaultconf.parallel,
            self.schedule,
            'Workload-1',
            True,
            'New Test')
        self.wait_for_workload_tobe_available(self.workload_id)
        self.date = time.strftime("%Y-%m-%d %H:%M:%S")
        self.end_date = datetime.strptime(
            self.date, "%Y-%m-%d %H:%M:%S") + timedelta(minutes=10)
        tvaultconf.sched.add_job(
            self.verifyScheduleTest,
            'interval',
            args=[
                self.workload_id],
            seconds=3558,
            id='my_job_id')
        tvaultconf.sched.start()
        if (tvaultconf.count < tvaultconf.No_of_Backup):
            raise Exception(" Scheduler is Not Running")
