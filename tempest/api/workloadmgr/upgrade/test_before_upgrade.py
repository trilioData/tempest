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
from tempest import command_argument_string
from tempest.util import cli_parser
import time

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
	          volume_id1 = self.create_volume()
                  self.workload_volumes.append(volume_id1)
                  vm_id = self.create_vm(vm_cleanup=False)
                  self.workload_instances.append(vm_id)
	          f.write("instance_id=" + str(self.workload_instances) + "\n") 
                  self.attach_volume(volume_id1, vm_id, device="/dev/vdb")
	          f.write("volume_ids=" + str(self.workload_volumes) + "\n")

	     #Create workload
             self.start_date = time.strftime("%x")
             self.start_time = time.strftime("%X")
             self.jobschedule = { "fullbackup_interval": "-1",
                                  "retention_policy_type": tvaultconf.retention_policy_type,
                                  "enabled": True,
                                  "start_date": self.start_date,
                                  "start_time": self.start_time,
                                  "interval": tvaultconf.interval,
                                  "retention_policy_value": tvaultconf.retention_policy_value }
             self.workload_id=self.workload_create(self.workload_instances,tvaultconf.parallel, self.jobschedule, workload_cleanup=False)
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

	     #Fetch workload scheduler and retention settings
	     self.scheduler_settings = self.getSchedulerDetails(self.workload_id)
	     LOG.debug("Workload scheduler settings: " + str(self.scheduler_settings))
	     f.write("scheduler_settings=" + str(self.scheduler_settings) + "\n")

             #Update user email in openstack
             self.update_user_email = self.update_user_email(CONF.identity.user_id, CONF.identity.user_email, CONF.identity.tenant_id)
             f.write("update_user_email_in_openstack=" + str(self.update_user_email) + "\n")
             if self.update_user_email:
                 reporting.add_test_step("Update email for user in openstack", tvaultconf.PASS)

                 #Fetch existing settings
                 self.existing_setting = self.get_settings_list()
                 LOG.debug("Existing setting list: " + str(self.existing_setting))
                 #Delete any existing settings
                 flag = False
                 if(self.existing_setting != {}):
                     for k,v in self.existing_setting.items():
                         if (self.delete_setting(k) == False):
                             flag = True
                 if flag:
                     reporting.add_test_step("Delete existing setting", tvaultconf.FAIL)
                 else:
                     #Update trilioVault email settings
                     self.settings_resp = self.update_email_setings(tvaultconf.setting_data)
                     f.write("settings_list=" + str(self.settings_resp) + "\n")
                     self.setting_data_from_resp = {}
                     for i in range(0,len(self.settings_resp)):
                         self.setting_data_from_resp[self.settings_resp[i]['name']] = self.settings_resp[i]['value']
                     LOG.debug("Settings data from response: " + str(self.setting_data_from_resp) + " ; original setting data: " + str(tvaultconf.setting_data))

                     if(cmp(self.setting_data_from_resp, tvaultconf.setting_data) == 0):
                         reporting.add_test_step("Update email settings", tvaultconf.PASS)

                         #Enable email notification for project
                         self.enable_email_resp = self.update_email_setings(tvaultconf.enable_email_notification)[0]
                         f.write("email_enabled_settings=" + str(self.enable_email_resp) + "\n")
                         if((str(self.enable_email_resp['name']) == 'smtp_email_enable') and (str(self.enable_email_resp['value']) == '1')):
                             reporting.add_test_step("Enable email notification for project", tvaultconf.PASS)
                         else:
                             reporting.add_test_step("Enable email notification for project", tvaultconf.FAIL)
                             reporting.set_test_script_status(tvaultconf.FAIL)
                     else:
                         reporting.add_test_step("Update email settings", tvaultconf.FAIL)
                         reporting.set_test_script_status(tvaultconf.FAIL)

             else:
                 reporting.add_test_step("Update email for user in openstack", tvaultconf.FAIL)
                 reporting.set_test_script_status(tvaultconf.FAIL)

             f.close()
	     reporting.test_case_to_write()

	except Exception as e:
	    LOG.error("Exception: " + str(e))
	    reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
