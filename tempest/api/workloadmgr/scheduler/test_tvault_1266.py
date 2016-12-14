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
sys.path.append("/opt/stack/tempest")
import apscheduler
from apscheduler.schedulers.blocking import BlockingScheduler
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



class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        cls.client = cls.os.wlm_client

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_create_workload(self):
        self.total_workloads=1
        self.vms_per_workload=1
        self.volume_size=1
        self.workload_instances = []
        self.workload_volumes = []
        self.workloads = []
        self.full_snapshots = []
        self.incr_snapshots = []
        self.snap_list = []
        self.restores = []
        self.start_date = time.strftime("%x")
        self.start_time = time.strftime("%X")
        self.end_date = timedelta(hours=1)
        self.enabled = True
        self.snapshot_type = []
        self.expected_type = ['full','incremental','full']
	self.schedule = {"fullbackup_interval": "1", "retention_policy_type": "Number of Snapshots to Keep", "enabled": self.enabled, "start_date": self.start_date, "start_time": self.start_time,"interval": tvaultconf.interval,"retention_policy_value": 4}
        self.description = "Full backup interval Number of Days with retention policy as No. of snapshot to keep"
        for vm in range(0,self.vms_per_workload):
             vm_id = self.create_vm()
             self.workload_instances.append(vm_id)
             volume_id = self.create_volume(self.volume_size,tvaultconf.volume_type)
             self.workload_volumes.append(volume_id)
             self.attach_volume(volume_id, vm_id)
        self.workload_id=self.workload_create(self.workload_instances,tvaultconf.parallel,self.schedule,'Workload-1',True,self.description)
        self.wait_for_workload_tobe_available(self.workload_id)
        self.assertEqual(self.getFullBackupIntervalStatus(self.workload_id), '1')
        self.date = time.strftime("%Y-%m-%d %H:%M:%S")
        self.end_date = datetime.strptime(self.date,"%Y-%m-%d %H:%M:%S")+timedelta(minutes=250)
        tvaultconf.sched.add_job(self.verifyScheduleTest,'interval',args=[self.workload_id],seconds=3558,id='my_job_id')
        tvaultconf.sched.start()
        self.snap_list = self.getSnapshotList(self.workload_id)
        for i in range(0,len(self.snap_list)):
            self.snapshot_type.append(self.getSnapshotTypeInfo(snap_list[i]))
            if (self.snapshot_type[i] == self.expected_type[i]):
                LOG.debug('Snapshot ID is : %s' % self.snap_list[i])
                LOG.debug('Snapshot Type is : %s' % self.snapshot_type[i])
            else :
                LOG.debug('Snapshot ID is : %s' % self.snap_list[i])
                LOG.debug('Snapshot Type is : %s' % self.snapshot_type[i])
                LOG.debug('Retention Policy Full backup interval Number of Days Failed')
                raise Exception("Retention Policy Full backup interval Number of Days Failed")
        LOG.debug('Retention Policy Full backup interval Number of Days Successful')

       

   
       
    
   
