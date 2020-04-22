import time
from tempest import reporting
from tempest import tvaultconf
from oslo_log import log as logging
from tempest import test
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
        cls.client = cls.os.wlm_client

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_1_tvault1157_1153_1154_1155_wlm_api_restart(self):
        reporting.add_test_script(str(__name__))
        try:
            # Change global job scheduler to disable using API
            status = self.disable_global_job_scheduler()
            if not status:
                reporting.add_test_step(
                    "Global job scheduler disable", tvaultconf.PASS)
                LOG.debug("Global job scheduler disabled successfully")
            else:
                reporting.add_test_step(
                    "Global job scheduler disable", tvaultconf.FAIL)
                raise Exception("Global job scheduler not disabled")

            # Execute wlm-api service restart
            status_update = self.restart_wlm_api_service()
            if "active (running)" in str(status_update):
                reporting.add_test_step(
                    "verify wlm-api service is up and running after restart", tvaultconf.PASS)
                LOG.debug("wlm-api service is up and running")
            else:
                reporting.add_test_step(
                    "verify wlm-api service is up and running after restart", tvaultconf.FAIL)
                raise Exception("wlm-api service is not restarted")

            # Verify global job scheduler remains disabled even after wlm-api service restart
            status = self.get_global_job_scheduler_status()
            if not status:
                reporting.add_test_step(
                    "Global job scheduler remains disabled after wlm-api service restart", tvaultconf.PASS)
                LOG.debug("Global job scheduler remains disabled")
            else:
                reporting.add_test_step(
                    "Global job scheduler remains disabled after wlm-api service restart", tvaultconf.FAIL)
                LOG.debug("Global job scheduler changed")

            # Change global job scheduler to enable using API
            status = self.enable_global_job_scheduler()
            if status:
                reporting.add_test_step(
                    "Global job scheduler enable", tvaultconf.PASS)
                LOG.debug("Global job scheduler enabled successfully")
            else:
                reporting.add_test_step(
                    "Global job scheduler enable", tvaultconf.FAIL)
                LOG.debug("Global job scheduler not enabled")

            # Execute wlm-api service restart
            status_update = self.restart_wlm_api_service()
            if "active (running)" in str(status_update):
                reporting.add_test_step(
                    "verify wlm-api service is up and running after restart", tvaultconf.PASS)
                LOG.debug("wlm-api service is up and running")
            else:
                reporting.add_test_step(
                    "verify wlm-api service is up and running after restart", tvaultconf.FAIL)
                raise Exception("wlm-api service is not restarted")

            # Verify global job scheduler remains enabled even after wlm-api service restart
            status = self.get_global_job_scheduler_status()
            if status:
                reporting.add_test_step(
                    "Global job scheduler remains enabled after wlm-api service restart", tvaultconf.PASS)
                LOG.debug("Global job scheduler remains enabled")
            else:
                reporting.add_test_step(
                    "Global job scheduler remains enabled after wlm-api service restart", tvaultconf.FAIL)
                LOG.debug("Global job scheduler changed")

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
