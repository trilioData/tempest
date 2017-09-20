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

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
	reporting.add_test_script(str(__name__))

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_tvault1062_bootfromvol_fullsnapshot(self):
	try:
	    self.total_workloads=1
            self.vms_per_workload=1
            self.volume_size=1
            self.workload_instances = []
            self.workload_volumes = []

            for vm in range(0,self.vms_per_workload):
                 volume_id1 = self.create_volume(image_id=CONF.compute.image_ref)
                 self.workload_volumes.append(volume_id1)
   	         self.set_volume_as_bootable(volume_id1)
	         self.block_mapping_details = [{ "source_type": "volume", 
				   "delete_on_termination": "false",
				   "boot_index": 0,
				   "uuid": volume_id1,
				   "destination_type": "volume" }]
	         vm_id = self.create_vm(image_id="", block_mapping_data=self.block_mapping_details)
	         self.workload_instances.append(vm_id)

            #Create workload
            self.workload_id=self.workload_create(self.workload_instances,tvaultconf.parallel)
            if (self.wait_for_workload_tobe_available(self.workload_id) == False):
                reporting.add_test_step("Create_Workload", tvaultconf.FAIL)
                raise Exception("Workload creation failed")
            self.workload_status = self.getWorkloadStatus(self.workload_id)

            #Create full snapshot
            self.snapshot_id=self.workload_snapshot(self.workload_id, True)
            self.wait_for_workload_tobe_available(self.workload_id)
            if(self.getSnapshotStatus(self.workload_id, self.snapshot_id) == "available"):
                reporting.add_test_step("Create full snapshot of boot from volume instance", tvaultconf.PASS)
            else:
                reporting.add_test_step("Create full snapshot of boot from volume instance", tvaultconf.FAIL)
                raise Exception("Snapshot creation failed")
	    reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

