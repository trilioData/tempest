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
    def test_tvault1033_create_workload(self):
        try:
            # Prerequisites
            self.created = False
            # Launch instance
            self.vm_id = self.create_vm()
            LOG.debug("VM ID: " + str(self.vm_id))

            # Create volume
            self.volume_id = self.create_volume()
            LOG.debug("Volume ID: " + str(self.volume_id))

            # Attach volume to the instance
            self.attach_volume(self.volume_id, self.vm_id)
            LOG.debug("Volume attached")

            # Create workload with CLI command
            workload_create = command_argument_string.workload_create + \
                " --instance instance-id=" + str(self.vm_id)
            rc = cli_parser.cli_returncode(workload_create)
            if rc != 0:
                reporting.add_test_step(
                    "Execute workload-create command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute workload-create command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            time.sleep(10)
            self.wid = query_data.get_workload_id(tvaultconf.workload_name)
            LOG.debug("Workload ID: " + str(self.wid))
            if(self.wid is not None):
                self.wait_for_workload_tobe_available(self.wid)
                if(self.getWorkloadStatus(self.wid) == "available"):
                    reporting.add_test_step("Create workload", tvaultconf.PASS)
                else:
                    reporting.add_test_step("Create workload", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Create workload", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # Cleanup
            # Delete workload
            self.workload_delete(self.wid)
            LOG.debug("Workload deleted successfully")
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
