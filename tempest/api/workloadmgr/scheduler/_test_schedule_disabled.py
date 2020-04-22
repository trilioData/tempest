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

import os
from tempest import tvaultconf
from tempest.common import waiters
from oslo_log import log as logging
from tempest import api
import time
import datetime
import json
from tempest import test
from tempest import config
from tempest.api.workloadmgr import base
from apscheduler.schedulers.blocking import BlockingScheduler
import apscheduler
import sys
sys.path.append("/opt/stack/tempest")
LOG = logging.getLogger(__name__)
CONF = config.CONF
# logging.basicConfig()
#sched = BlockingScheduler()


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
        self.full_snapshots = []
        self.incr_snapshots = []
        self.restores = []
        self.start_date = time.strftime("%x")
        self.start_time = time.strftime("%X")
        self.enabled = False
        self.schedule = {"interval": tvaultconf.interval, "enabled": self.enabled,
                         "start_date": self.start_date, "start_time": self.start_time}
        for vm in range(0, self.vms_per_workload):
            vm_id = self.create_vm()
            self.workload_instances.append(vm_id)
            volume_id = self.create_volume(
                self.volume_size, tvaultconf.volume_type)
            self.workload_volumes.append(volume_id)
            self.attach_volume(volume_id, vm_id)
        print self.schedule
        self.workload_id = self.workload_create(
            self.workload_instances, tvaultconf.parallel, self.schedule)
        self.wait_for_workload_tobe_available(self.workload_id)
        self.assertEqual(self.getSchedulerStatus(self.workload_id), False)
        #self.SchedulerStatus = True
        # if (self.is_scheduler_enabled(self.workload_id) == True):
        #	print " Scheduler is enable "
        # else :
        #	print " Scheduler is disabled "
