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
import os
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
        self.snap_list = []
        file = open("Tvault-1268.txt", "r")
        self.workload = file.read().splitlines()
        self.workload_id = self.workload[0]
        self.volume_id = self.workload[1]
        self.server_id = self.workload[2]
        self.assertEqual(self.getRetentionPolicyTypeStatus(
            self.workload_id), 'Number of Snapshots to Keep')
        self.assertEqual(
            self.getRetentionPolicyValueStatus(self.workload_id), 2)
        self.snap_list = self.getSnapshotList(self.workload_id)
        if (len(self.snap_list) == 2):
            LOG.debug('No. of snapshot %s' % (len(self.snap_list)))
            LOG.debug(
                'At any point of time there are only N snapshots stored on the disk where N is "Number of Snapshots to Keep"  ')
        else:
            LOG.debug(
                'Retention Policy No. of snapshot to keep is not working properly')
            LOG.debug('No. of snapshot %s' % (len(self.snap_list)))
            raise Exception("Retention Policy No. of snapshot to keep Failed")

        for i in range(0, len(self.snap_list)):
            self.snapshot_delete(self.workload_id, self.snap_list[i])
        self.workload_delete(self.workload_id)
        self.detach_volume(self.server_id, self.volume_id)
        self.vol_snapshot_list = self.get_volume_snapshots(self.volume_id)
        for i in range(0, len(self.vol_snapshot_list)):
            LOG.debug('Volume Snapshot ID is : %s' % self.vol_snapshot_list[i])
            self.delete_volume_snapshot(self.vol_snapshot_list[i])
        self.delete_vm(self.server_id)
        self.delete_volume(self.volume_id)
        os.remove('Tvault-1267.txt')
