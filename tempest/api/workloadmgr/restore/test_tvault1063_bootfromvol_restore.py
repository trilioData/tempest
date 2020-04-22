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

    @test.pre_req({'type': 'bootfromvol_workload'})
    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_tvault1063_bootfromvol_restore(self):
        try:

            # Create full snapshot
            self.snapshot_id = self.workload_snapshot(self.workload_id, True)
            self.wait_for_workload_tobe_available(self.workload_id)
            if(self.getSnapshotStatus(self.workload_id, self.snapshot_id) == "available"):
                reporting.add_test_step(
                    "Create full snapshot of boot from volume instance", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Create full snapshot of boot from volume instance", tvaultconf.FAIL)
                raise Exception("Snapshot creation failed")

            self.delete_vms(self.workload_instances)

            # Trigger oneclick restore
            self.restore_id = self.snapshot_restore(
                self.workload_id, self.snapshot_id)
            self.wait_for_workload_tobe_available(self.workload_id)
            if(self.getRestoreStatus(self.workload_id, self.snapshot_id, self.restore_id) == "available"):
                reporting.add_test_step(
                    "Oneclick restore of boot from volume instance", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Oneclick restore of boot from volume instance", tvaultconf.FAIL)
                raise Exception("Oneclick restore failed")
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
