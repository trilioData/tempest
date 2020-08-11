from tempest.util import query_data
from tempest.util import cli_parser
from tempest import command_argument_string
import time
from tempest import reporting
from tempest import tvaultconf
from oslo_log import log as logging
from tempest.lib import decorators
from tempest import config
from tempest.api.workloadmgr import base
import sys
import os
sys.path.append(os.getcwd())

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()
        reporting.add_test_script(str(__name__))

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_tvault1039_delete_workload(self):
        try:
            # Prerequisites
            self.deleted = False
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
                workload_name=tvaultconf.workload_name,
                workload_cleanup=False)
            LOG.debug("Workload ID: " + str(self.wid))
            time.sleep(5)

            # Delete workload from CLI command
            rc = cli_parser.cli_returncode(
                command_argument_string.workload_delete + str(self.wid))
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-delete command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-delete command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            wc = query_data.get_deleted_workload(self.wid)
            LOG.debug("Workload status: " + str(wc))
            if(str(wc) == "deleted"):
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.PASS)
                LOG.debug("Workload successfully deleted")
                self.deleted = True
            else:
                while (str(wc) != "deleted"):
                    time.sleep(5)
                    wc = query_data.get_deleted_workload(self.wid)
                    LOG.debug("Workload status: " + str(wc))
                    if (str(wc) == "deleted"):
                        reporting.add_test_step(
                            "Verification with DB", tvaultconf.PASS)
                        LOG.debug("Workload successfully deleted")
                        self.deleted = True
                        break
            if (self.deleted == False):
                reporting.add_test_step(
                    "Verification with DB", tvaultconf.FAIL)
                raise Exception("Workload did not get deleted")
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
