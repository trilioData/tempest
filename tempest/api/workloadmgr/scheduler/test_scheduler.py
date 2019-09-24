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
from tempest import test
import json
import sys
import time
import os
from datetime import datetime, timedelta
from tempest import api
from oslo_log import log as logging
from tempest.common import waiters
from tempest import tvaultconf
from tempest import reporting
sys.path.append(os.getcwd())
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
    def test_scheduler(self):
        try:
            retention = 3 
            start_date = time.strftime("%x")
            start_time = (datetime.now()+timedelta(minutes=5)).strftime("%H:%M:%S")
            self.schedule = {"fullbackup_interval": "0", "retention_policy_type": "Number of Snapshots to Keep", "interval": tvaultconf.interval, "enabled": True, "start_date": start_date, "start_time": start_time, "retention_policy_value": retention}
            vmid = self.create_vm(vm_cleanup=True)
            volume = self.create_volume(volume_cleanup=True)
            self.attach_volume(volume, vmid, attach_cleanup=True)
            wid=self.workload_create([vmid],tvaultconf.parallel,self.schedule,'Workload-1',True,'New Test')
            if(wid != None):
                self.wait_for_workload_tobe_available(wid)
                if(self.getWorkloadStatus(wid) == "available"):
                    reporting.add_test_step("Create workload", tvaultconf.PASS)
                else:
                    reporting.add_test_step("Create workload", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Create workload", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("Workload creation failed")
            LOG.debug("Sleeping till snapshots get completed")
            time.sleep((int(tvaultconf.interval.split(' ')[0])*int((retention+1))*3600)+600)
            
            snapshots = self.getSnapshotList(workload_id=wid)
            snaptimes = []
            snapshots1 = [x for x in snapshots if self.getSnapshotStatus(wid,x)=='available']
            diff_list = []
            if len(snapshots1) == retention:
                LOG.debug("Retention passed")
                reporting.add_test_step("Retention", tvaultconf.PASS)
                for snapshot in snapshots:
                    info = self.getSnapshotInfo(snapshot_id=snapshot)
                    t1 = str(self.wlm_client.client.get("/snapshots/"+snapshot)[1]['snapshot']['created_at'])
                    snaptimes.append(datetime.strptime(t1, '%Y-%m-%dT%H:%M:%S.%f'))
                     
                    if info[2] == "full" and self.getSnapshotStatus(wid,snapshot)=='available':
                        pass
                    else:
                        raise Exception("Incremental snapshots instead of full")
            else:
                LOG.debug("Retention passed")
                reporting.add_test_step("Retention", tvaultconf.FAIL)
                raise Exception("Retention failed")
            for x, y in zip(snaptimes[0::], snaptimes[1::]): 
                diff_list.append(y-x)
            if len(set(diff_list)) == 1:
                LOG.debug("Scheduler is working correctly")
                reporting.add_test_step("Scheduler", tvaultconf.PASS)
            else:
                LOG.debug("Scheduler isn't working correctly")
                reporting.add_test_step("Scheduler", tvaultconf.FAIL)

            reporting.test_case_to_write() 

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write() 
