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
import time
import datetime
LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(self):
        super(WorkloadsTest, self).setup_clients()

    @test.attr(type='smoke')
    @test.idempotent_id('3d64b5d3-b083-418c-82de-2b3394e57925')
    def test_create_workload_from_file(self):
        self.total_workloads=100
        self.vms_per_workload=2
        self.workloads = []
        self.full_snapshots = []
        #self.workload_instances = []
        self.workload_volumes = []
        self.incr_snapshots = []
        self.restores = []
        self.enabled = True
        self.a_zone_count=0
        volumes = ["/dev/vdb"]
        mount_points = ["mount_data_b"]
        a_zones=["compute1","compute2","compute3","compute4","compute5"]
        self.security_group_details = self.create_security_group(tvaultconf.security_group_name)
        security_group_id = self.security_group_details['security_group']['id']
        LOG.debug("security group rules" + str(self.security_group_details['security_group']['rules']))
        for workload in range(0,self.total_workloads):
            self.workload_instances = []
            workload_volumes = []
            for vm in range(0,self.vms_per_workload):
               vm_id = self.create_vm()
               LOG.debug("vm_id from file: " + str(vm_id))
               self.workload_instances.append(vm_id.strip())
            LOG.debug("Workload instances: " + str(self.workload_instances))
        # for workload in range(0,self.total_workloads):
            self.workload_start_date=datetime.datetime.now()
            self.start_date = self.workload_start_date.strftime("%Y-%m-%d")
            self.start_time = self.workload_start_date.strftime("%H:%M:%S")
            self.schedule = {"fullbackup_interval": "-1", "retention_policy_type": "Number of Snapshots to Keep", "enabled": self.enabled, "start_date": self.start_date, "start_time": self.start_time,"interval": tvaultconf.interval,"retention_policy_value": 3}
            self.workload_id=self.workload_create(self.workload_instances,self.schedule)
            self.workloads.append(self.workload_id)

