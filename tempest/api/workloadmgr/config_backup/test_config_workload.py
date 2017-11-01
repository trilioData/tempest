import sys
import os
sys.path.append(os.getcwd())
from tempest.api.workloadmgr import base
from tempest import config
from tempest import test
from oslo_log import log as logging
from tempest import tvaultconf
from tempest import reporting
import time
from tempest import command_argument_string
from tempest.util import cli_parser
from tempest.util import query_data

LOG = logging.getLogger(__name__)
CONF = config.CONF

class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()
        cls.client = cls.os.wlm_client

    @test.pre_req({'type':'config_backup'})
    @test.attr(type='smoke')
    @test.idempotent_id('72fe87ca-541a-42b0-b83a-1e07a5420603')
    def test_1_config_workload_configure(self):
        reporting.add_test_script(str(__name__) + "_configure")
        try:
            # prerequisite handles config_user creation and config_backup_pvk(private key) creation
            
            # for config backup configuration, yaml_file creation 
            self.create_config_backup_yaml()

            # config backup configuration with CLI command
            config_workload_command = "workloadmgr config-workload-configure --config-file yaml_file --authorized-key " \
                                    "config_backup_pvk "
    
            LOG.debug("config workload configure cli command: " + str(config_workload_command))
    
            rc = cli_parser.cli_returncode(config_workload_command)
            if rc != 0:
                reporting.add_test_step("Triggering config_workload_configure command via CLI", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step("Triggering config_workload_configure command via CLI", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()


    @test.attr(type='smoke')
    @test.idempotent_id('ae78e629-1499-451b-b82e-6165b269863d')
    def test_2_config_workload_show(self):
        reporting.add_test_script(str(__name__) + "_show_cli")
        try:
	    # test config_workload_show cli
            config_workload_show_command = "workloadmgr config-workload-show"

            LOG.debug("config workload show cli command: " + str(config_workload_show_command))

            rc = cli_parser.cli_returncode(config_workload_show_command)
            if rc != 0:
                reporting.add_test_step("Triggering config_workload_show_command via CLI", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step("Triggering config_workload_show_command via CLI", tvaultconf.PASS)
                LOG.debug("Command executed correctly") 

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @test.attr(type='smoke')
    @test.idempotent_id('52d14575-e2dd-46bf-b1f2-7c317121fc6e')
    def test_3_config_workload_get_api(self):
        reporting.add_test_script(str(__name__) + "get_api")
        try:
	    # test config_workload get api
            config_workload_output = self.get_config_workload()

            config_workload_status = config_workload_output['status']

            if config_workload_status == "available":
                LOG.debug("config_workload status is available, config_workload_id: " + config_workload_output['id'])
                reporting.add_test_step("config_workload status: available", tvaultconf.PASS)
            else:
                LOG.debug("config_workload status is not available, Error msg: " + config_workload_output['error_msg'])
                reporting.add_test_step("config_workload status: " + config_workload_output['status'], tvaultconf.FAIL) 

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @test.attr(type='smoke')
    @test.idempotent_id('3c18e818-42b9-40fb-9dcc-2a0ac36332e0')
    def test_4_config_workload_scheduler_disable(self):
        reporting.add_test_script(str(__name__) + "_scheduler_disable")
        try:
	    # config_workload_scheduler_disable cli test
            config_workload_scheduler_disable_command = "workloadmgr config-workload-scheduler-disable"

            LOG.debug("config-workload-scheduler-disable cli command: " + str(config_workload_scheduler_disable_command))

            rc = cli_parser.cli_returncode(config_workload_scheduler_disable_command)
	    
	    if rc != 0:
		LOG.debug("config_workload scheduler disable cli not successfull")
                reporting.add_test_step("config_workload_scheduler_disable cli", tvaultconf.FAIL)
	    else:
		LOG.debug("config_workload scheduler disable cli successfull")
                reporting.add_test_step("config_workload_scheduler_disable cli", tvaultconf.PASS)

	    # test config_workload get api
            config_workload_output = self.get_config_workload()

            jobschedule_status = str(config_workload_output['jobschedule']['enabled'])

            if jobschedule_status == "False":
                LOG.debug("config_workload scheduler status: " + jobschedule_status)
                reporting.add_test_step("config_workload scheduler status: " + jobschedule_status, tvaultconf.PASS)
            else:
		LOG.debug("config_workload scheduler status: " + jobschedule_status)
                reporting.add_test_step("config_workload scheduler status: " + jobschedule_status, tvaultconf.FAIL)
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
