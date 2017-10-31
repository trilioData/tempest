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
	reporting.add_test_script(str(__name__))

    @test.pre_req({'type':'config_backup'})
    @test.attr(type='smoke')
    @test.idempotent_id('9fe07170-912e-49a5-a629-5f52eeada4c9')
    def test_config_backup(self):
	try:
	    # prerequisite handles config_user creation and config_backup_pvk(private key) creation
	    
	    # for config backup configuration, yaml_file creation 
	    self.create_config_backup_yaml()

	    self.calculate_md5_sum_before_config_backup() 
	
	    reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

