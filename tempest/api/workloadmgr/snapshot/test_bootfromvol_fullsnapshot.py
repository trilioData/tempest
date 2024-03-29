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

from oslo_log import log as logging

from tempest import config
from tempest import reporting
from tempest import test
from tempest import tvaultconf
from tempest.api.workloadmgr import base
from tempest.lib import decorators

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        reporting.add_test_script(str(__name__))

    @test.pre_req({'type': 'bootfromvol_workload'})
    @decorators.attr(type='smoke')
    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    @decorators.attr(type='workloadmgr_api')
    def test_bootfromvol_fullsnapshot(self):
        try:
            # Create full snapshot
            self.snapshot_id = self.workload_snapshot(
                self.workload_id, True, snapshot_cleanup=False)
            self.wait_for_workload_tobe_available(self.workload_id)
            if(self.getSnapshotStatus(self.workload_id, self.snapshot_id) == "available"):
                reporting.add_test_step(
                    "Create full snapshot of boot from volume instance",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Create full snapshot of boot from volume instance",
                    tvaultconf.FAIL)
                raise Exception("Snapshot creation failed")

            # Cleanup
            # Delete Snapshot
            self.snapshot_delete(self.workload_id, self.snapshot_id)

            # Delete volume
            self.volume_snapshots = self.get_available_volume_snapshots()
            self.delete_volume_snapshots(self.volume_snapshots)

            # Delete workload
            self.workload_delete(self.workload_id)

            # Delete vm
            self.delete_vm(self.vm_id)

            # Delete volume
            self.delete_volume(self.volume_id)

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
