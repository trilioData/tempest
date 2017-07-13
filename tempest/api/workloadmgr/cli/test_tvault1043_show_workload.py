import sys
import os
import json
sys.path.append(os.getcwd())
from tempest.api.workloadmgr import base
from tempest import config
from tempest import test
from oslo_log import log as logging
from tempest import tvaultconf, reporting
from tempest.api.workloadmgr.cli.config import command_argument_string
from tempest.api.workloadmgr.cli.util import cli_parser, query_data, db_handler

LOG = logging.getLogger(__name__)
CONF = config.CONF

class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
	reporting.add_test_script(str(__name__))

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_tvault1043_show_workload(self):
        #Prerequisites
        self.created = False
        self.workload_instances = []
        #Launch instance
        self.vm_id = self.create_vm()
        LOG.debug("VM ID: " + str(self.vm_id))

        #Create volume
        self.volume_id = self.create_volume(tvaultconf.volume_size,tvaultconf.volume_type)
        LOG.debug("Volume ID: " + str(self.volume_id))
        
        #Attach volume to the instance
        self.attach_volume(self.volume_id, self.vm_id)
        LOG.debug("Volume attached")

        #Create workload
        self.workload_instances.append(self.vm_id)
        self.wid = self.workload_create(self.workload_instances, tvaultconf.parallel, workload_name=tvaultconf.workload_name)
        LOG.debug("Workload ID: " + str(self.wid))
        
        #Show workload details using CLI command
        rc = cli_parser.cli_returncode(command_argument_string.workload_show + self.wid)
        if rc != 0:
	    reporting.add_test_step("Execute workload-show command", tvaultconf.FAIL)
            raise Exception("Command did not execute correctly")
        else:
	    reporting.add_test_step("Execute workload-show command", tvaultconf.PASS)
            LOG.debug("Command executed correctly")
            
        #Compare the workload details against database
        out = cli_parser.cli_output(command_argument_string.workload_show + self.wid)
        LOG.debug("Response from DB: " + str(out))
        
        if(query_data.get_workload_display_name(self.wid) == cli_parser.cli_response_parser(out, 'name')):
	    reporting.add_test_step("Verify workload name", tvaultconf.PASS)
	else:
	    reporting.add_test_step("Verify workload name", tvaultconf.FAIL)
	if(query_data.get_workload_display_description(self.wid) == cli_parser.cli_response_parser(out, 'description')):
            reporting.add_test_step("Verify workload description", tvaultconf.PASS)
        else:
            reporting.add_test_step("Verify workload description", tvaultconf.FAIL)
        if(query_data.get_workload_status_by_id(self.wid) == cli_parser.cli_response_parser(out, 'status')):
            reporting.add_test_step("Verify workload status", tvaultconf.PASS)
        else:
            reporting.add_test_step("Verify workload status", tvaultconf.FAIL)
        
        instances_cli = []
        temp = json.loads(cli_parser.cli_response_parser(out,'instances'))
        for i in range(0, len(temp)):
            instances_cli.append(temp[i]['id'])
        instances_cli.sort()        
        instances_db = query_data.get_workload_vmids(self.wid)
        instances_db.sort()
	if(instances_db == instances_cli):
            reporting.add_test_step("Verify workload instances", tvaultconf.PASS)
        else:
            reporting.add_test_step("Verify workload instances", tvaultconf.FAIL)
