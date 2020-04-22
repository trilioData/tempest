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
LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']
    workload_id = ''

    @classmethod
    def setup_clients(self):
        super(WorkloadsTest, self).setup_clients()

    @test.attr(type='smoke')
    @test.idempotent_id('3d64b5d3-b283-418c-82de-2b3394e57925')
    def test_1(self):
        snapshot_list = self.snapshots_extensions_client.list_snapshots()[
            'snapshots']
        LOG.debug("Snapshot list" + str(snapshot_list))
        for snapshot in snapshot_list:
            LOG.debug("Deleting snapshot:" + snapshot['id'])
            self.snapshots_extensions_client.delete_snapshot(snapshot['id'])
