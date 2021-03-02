import os
import sys
import time

from oslo_log import log as logging

from tempest import command_argument_string
from tempest import config
from tempest import reporting
from tempest import tvaultconf
from tempest.api.workloadmgr import base
from tempest.lib import decorators
from tempest.util import cli_parser
from tempest.util import query_data

sys.path.append(os.getcwd())

LOG = logging.getLogger(__name__)
CONF = config.CONF


class RestoreTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(RestoreTest, cls).setup_clients()
        reporting.add_test_script(str(__name__))

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    @decorators.attr(type='workloadmgr_cli')
    def test_tvault1037_list_restore(self):
        try:
            # Prerequisites
            self.created = False
            self.workload_instances = []

            # Launch instance
            self.vm_id = self.create_vm()
            LOG.debug("VM ID: " + str(self.vm_id))

            # Create volume
            self.volume_id = self.create_volume()
            LOG.debug("Volume ID: " + str(self.volume_id))

            # Attach volume to the instance
            self.attach_volume(self.volume_id, self.vm_id)
            LOG.debug("Volume attached")

            # Create workload
            self.workload_instances.append(self.vm_id)
            self.wid = self.workload_create(
                self.workload_instances,
                tvaultconf.parallel,
                workload_name=tvaultconf.workload_name)
            LOG.debug("Workload ID: " + str(self.wid))
            time.sleep(5)

            # Create snapshot
            self.snapshot_id = self.workload_snapshot(
                self.wid, True, tvaultconf.snapshot_name)
            LOG.debug("Snapshot ID: " + str(self.snapshot_id))
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id)

            # Delete instance
            self.delete_vm(self.vm_id)
            LOG.debug("Instance deleted successfully")

            # Delete corresponding volume
            self.delete_volume(self.volume_id)
            LOG.debug("Volume deleted successfully")

            # Create one-click restore
            self.restore_id = self.snapshot_restore(
                self.wid, self.snapshot_id, tvaultconf.restore_name)
            LOG.debug("Restore ID: " + str(self.restore_id))

            # Wait till restore is complete
            wc = query_data.get_snapshot_restore_status(
                tvaultconf.restore_name, self.snapshot_id)
            LOG.debug("Snapshot restore status: " + str(wc))
            while (str(wc) != "available" or str(wc) != "error"):
                time.sleep(5)
                wc = query_data.get_snapshot_restore_status(
                    tvaultconf.restore_name, self.snapshot_id)
                LOG.debug("Snapshot restore status: " + str(wc))
                if (str(wc) == "available"):
                    LOG.debug("Snapshot Restore successfully completed")
                    self.created = True
                    break
                else:
                    if (str(wc) == "error"):
                        break

            if (self.created == False):
                reporting.add_test_step("One click Restore", tvaultconf.FAIL)
                raise Exception("Snapshot Restore did not get created")

            # List Restores using CLI command
            rc = cli_parser.cli_returncode(
                command_argument_string.restore_list)
            if rc != 0:
                reporting.add_test_step(
                    "Execute restore-list command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute restore-list command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            wc = query_data.get_available_restores()
            out = cli_parser.cli_output(command_argument_string.restore_list)
            if (int(wc) == int(out)):
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.PASS)
                LOG.debug(
                    "Restore list command listed available restores correctly")
            else:
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.FAIL)
                raise Exception(
                    "Restore list command did not list available restores correctly")
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
