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
from tempest.api.workloadmgr.cli.config import command_argument_string
from tempest.api.workloadmgr.cli.util import cli_parser

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
    def test_before_upgrade(self):
        self.vms_per_workload=1
        self.volume_size=1
        self.workload_instances = []
        self.workload_volumes = []
	self.test_json = {}

	try:
	     f = open("tempest/upgrade_data_conf.py", "w")
             for vm in range(0,self.vms_per_workload):
	          volume_id1 = self.create_volume(self.volume_size,tvaultconf.volume_type)
                  self.workload_volumes.append(volume_id1)
                  vm_id = self.create_vm(vm_cleanup=False)
                  self.workload_instances.append(vm_id)
	          f.write("instance_id=" + str(self.workload_instances) + "\n") 
                  self.attach_volume(volume_id1, vm_id, device="/dev/vdb")
	          f.write("volume_ids=" + str(self.workload_volumes) + "\n")

             #Create workload
             self.workload_id=self.workload_create(self.workload_instances,tvaultconf.parallel, workload_cleanup=False)
             if(self.wait_for_workload_tobe_available(self.workload_id)):
                  reporting.add_test_step("Create Workload", tvaultconf.PASS)
             else:
                  reporting.add_test_step("Create Workload", tvaultconf.FAIL)
                  raise Exception("Workload creation failed")
	     f.write("workload_id=\"" + str(self.workload_id) + "\"\n")

             #Create full snapshot
             self.snapshot_id=self.workload_snapshot(self.workload_id, True, snapshot_cleanup=False)
             self.wait_for_workload_tobe_available(self.workload_id)
             if(self.getSnapshotStatus(self.workload_id, self.snapshot_id) == "available"):
                  reporting.add_test_step("Create Snapshot", tvaultconf.PASS)
             else:
                  reporting.add_test_step("Create Snapshot", tvaultconf.FAIL)
                  raise Exception("Snapshot creation failed")
	     f.write("full_snapshot_id=\"" + str(self.snapshot_id) + "\"\n")

	     #Get global job scheduler status
	     self.scheduler_status = self.get_global_job_scheduler_status()
	     if(self.scheduler_status == tvaultconf.global_job_scheduler):
		LOG.debug("Global job scheduler status before upgrade: " + str(self.scheduler_status))
		reporting.add_test_step("Global job scheduler " + str(self.scheduler_status), tvaultconf.PASS)
	     else:
	        if(tvaultconf.global_job_scheduler == 'true'):
		    self.scheduler_status = self.enable_global_job_scheduler()
		    if (self.scheduler_status == 'false'):
			reporting.add_test_step("Enable global job scheduler", tvaultconf.FAIL)
			raise Exception("Enable global job scheduler failed")
		    else:
			reporting.add_test_step("Enable global job scheduler", tvaultconf.PASS)
		else:
                    self.scheduler_status = self.disable_global_job_scheduler()
                    if (self.scheduler_status == 'true'):
                        reporting.add_test_step("Disable global job scheduler", tvaultconf.FAIL)
                        raise Exception("Disable global job scheduler failed")
                    else:
                        reporting.add_test_step("Disable global job scheduler", tvaultconf.PASS)
             f.close()
	     reporting.test_case_to_write()

	except Exception as e:
	    LOG.error("Exception: " + str(e))
	    reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
