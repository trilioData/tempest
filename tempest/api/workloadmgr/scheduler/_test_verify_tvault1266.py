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
from tempest.lib import decorators
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

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_create_workload(self):
        self.expected_type = ['full', 'incremental', 'full']
        self.snap_list = []
        self.snapshot_type = []
        #file = open("Tvault-1266.txt", "r")
        for line in open("Tvault-1264.txt", "r"):
            if 'workload_id' in line:
                self.workload_info = line.split('=')
                self.workload_id = self.workload_info[1].strip()
            if 'volume_id' in line:
                self.volume_info = line.split('=')
                self.volume_id = self.volume_info[1].strip()
            if 'vm_id' in line:
                self.vm_info = line.split('=')
                self.server_id = self.vm_info[1].strip()

        self.workload = file.read().splitlines()
        self.workload_id = self.workload[0]
        self.volume_id = self.workload[1]
        self.server_id = self.workload[2]
        LOG.debug('Workload ID is : %s' % self.workload_id)
        self.assertEqual(
            self.getFullBackupIntervalStatus(self.workload_id), '1')
        if(self.is_schedule_running(self.workload_id)):
            self.snap_list = self.getSnapshotList(self.workload_id)
            for i in range(0, len(self.snap_list), 2):
                self.snapshot_info = getSnapshotInfo(self.snap_list[i])
                self.snapshot_type.append(self.snapshot_info[2])
                if (self.snapshot_type[i] == 'full'):
                    LOG.debug('Snapshot ID is : %s' % self.snap_list[i])
                    LOG.debug('Snapshot Type is : %s' % self.snapshot_type[i])
                else:
                    LOG.debug('Snapshot ID is : %s' % self.snap_list[i])
                    LOG.debug('Snapshot Type is : %s' % self.snapshot_type[i])
                    LOG.debug(
                        'Retention Policy Full backup interval Number of Days Failed')
                    raise Exception(
                        "Retention Policy Full backup interval Number of Days Failed")
            for i in range(1, len(self.snap_list), 2):
                self.snapshot_info = getSnapshotInfo(self.snap_list[i])
                self.snapshot_type.append(self.snapshot_info[2])
                if (self.snapshot_type[i] == 'incremental'):
                    LOG.debug('Snapshot ID is : %s' % self.snap_list[i])
                    LOG.debug('Snapshot Type is : %s' % self.snapshot_type[i])
                else:
                    LOG.debug('Snapshot ID is : %s' % self.snap_list[i])
                    LOG.debug('Snapshot Type is : %s' % self.snapshot_type[i])
                    LOG.debug(
                        'Retention Policy Full backup interval Number of Days Failed')
                    raise Exception(
                        "Retention Policy Full backup interval Number of Days Failed")
        else:
            LOG.debug(
                'Retention Policy Full backup interval Number of Days Failed')

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
        self.delete_vm(self.server_id)
        os.remove('Tvault-1266.txt')
