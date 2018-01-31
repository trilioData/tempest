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
from tempest import reporting
from datetime import datetime

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        cls.client = cls.os.wlm_client


    def _attached_volume_prerequisite(self, volume_type):
        self.vm_id = self.create_vm()
        if(volume_type == "LVM"):
            self.volume_id = self.create_volume(volume_type_id=CONF.volume.volume_type_id_1)
        else:
            self.volume_id = self.create_volume()
        self.attach_volume(self.volume_id, self.vm_id, device="/dev/vdb")


    def _create_workload(self, workload_instances):
        self.workload_id=self.workload_create(workload_instances,tvaultconf.parallel, workload_cleanup=False)
        self.wait_for_workload_tobe_available(self.workload_id)
        self.workload_status = self.getWorkloadStatus(self.workload_id)


    def _create_full_snapshot(self):
        self.snapshot_id=self.workload_snapshot(self.workload_id, True, snapshot_cleanup=False)
        self.snapshot_status = self.getSnapshotStatus(self.workload_id, self.snapshot_id)


    def _wait_for_workload(self, workload_id, snapshot_id):
        self.wait_for_workload_tobe_available(workload_id)
        return self.getSnapshotStatus(workload_id, snapshot_id)


    def _delete_snapshot(self, workload_id, snapshot_id):
        return self.snapshot_delete(workload_id, snapshot_id)


    def _delete_workload(self, workload_id):
        return self.workload_delete(workload_id)


    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_create_full_snapshot(self):
        result_json = {}
        for test in tvaultconf.enabled_tests:
            result_json[test] = {}
        LOG.debug("Result json: " + str(result_json))

        for k in result_json.keys():
             if(k.find("Attach") != -1):
                 if(k.find("Ceph") != -1):
                     self._attached_volume_prerequisite("Ceph")
                 else:
                     self._attached_volume_prerequisite("LVM")
             result_json[k]['instances'] = self.vm_id
             result_json[k]['volumes'] = self.volume_id
             self._create_workload([self.vm_id])
             result_json[k]['result'] = {}
             result_json[k]['workload'] = self.workload_id
             result_json[k]['workload_status'] = self.workload_status
             if(self.workload_status == "available"):
                 result_json[k]['result']['Create_Workload'] = tvaultconf.PASS
             else:
                 result_json[k]['result']['Create_Workload'] = tvaultconf.FAIL
                 continue

             self._create_full_snapshot()
             result_json[k]['snapshot'] = self.snapshot_id
             result_json[k]['snapshot_status'] = self.snapshot_status

        LOG.debug("Result json: " + str(result_json))

        for k in result_json.keys():
             result_json[k]['snapshot_status'] = self._wait_for_workload(result_json[k]['workload'], result_json[k]['snapshot'])
             if(result_json[k]['snapshot_status'] == "available"):
                 result_json[k]['result']['Create_Snapshot'] = tvaultconf.PASS
             else:
                 result_json[k]['result']['Create_Snapshot'] = tvaultconf.FAIL
                 continue

        LOG.debug("Final Result json: " + str(result_json))

        #Add results to sanity report
        for k,v in result_json.items():
             for k1,v1 in v['result'].items():
                 reporting.add_sanity_results(k1+"_"+k, v1)

