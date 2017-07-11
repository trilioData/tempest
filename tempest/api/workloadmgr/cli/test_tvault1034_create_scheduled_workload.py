import sys
import os
sys.path.append(os.getcwd())
from tempest.api.workloadmgr import base
from tempest import config
from tempest import test
from oslo_log import log as logging
from tempest import tvaultconf, reporting
import time
from tempest.api.workloadmgr.cli.config import command_argument_string
from tempest.api.workloadmgr.cli.util import cli_parser, query_data

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
    def test_tvault1034_create_scheduled_workload(self):
        #Prerequisites
        self.created = False
        #Launch instance
        self.vm_id = self.create_vm()
        LOG.debug("VM ID: " + str(self.vm_id))

        #Create volume
        self.volume_id = self.create_volume(tvaultconf.volume_size,tvaultconf.volume_type)
        LOG.debug("Volume ID: " + str(self.volume_id))
        
        #Attach volume to the instance
        self.attach_volume(self.volume_id, self.vm_id)
        LOG.debug("Volume attached")

        #Create workload with CLI command
        self.start_date = time.strftime("%x")
        self.start_time = time.strftime("%I:%M %p")
        interval = tvaultconf.interval
        retention_policy_type = tvaultconf.retention_policy_type
        retention_policy_value = tvaultconf.retention_policy_value
        workload_create = command_argument_string.workload_create + " --instance instance-id=" +str(self.vm_id)\
            + " --jobschedule start_date=" + str(self.start_date) + " --jobschedule start_time='" + str(self.start_time)\
            + "' --jobschedule interval='" + str(interval) + "' --jobschedule retention_policy_type='"\
            + str(retention_policy_type) + "' --jobschedule retention_policy_value=" + str(retention_policy_value)\
	    + " --jobschedule enabled=True"
        rc = cli_parser.cli_returncode(workload_create)
        if rc != 0:
	    reporting.add_test_step("Execute workload-create command with scheduler enabled", tvaultconf.FAIL)
            raise Exception("Command did not execute correctly")
        else:
	    reporting.add_test_step("Execute workload-create command with scheduler enabled", tvaultconf.PASS)
            LOG.debug("Command executed correctly")
        
        wc = query_data.get_workload_status(tvaultconf.workload_name)
        LOG.debug("Workload status: " + str(wc))
        while (str(wc) != "available" or str(wc)!= "error"):
            time.sleep(10)
            wc = query_data.get_workload_status(tvaultconf.workload_name)
            LOG.debug("Workload status: " + str(wc))
            if (str(wc) == "available"):
                LOG.debug("Workload successfully created")
		reporting.add_test_step("Workload status updated to available", tvaultconf.PASS)
                self.created = True
                break
            else:
                if (str(wc) == "error"):
		    reporting.add_test_step("Workload status updated to error", tvaultconf.FAIL)
                    break
        if (self.created == False):
            raise Exception ("Workload did not get created")
        
        self.wid = query_data.get_workload_id(tvaultconf.workload_name)
        LOG.debug("Workload ID: " + str(self.wid))
        
        self.schedule = query_data.get_workload_schedule(self.wid)
        LOG.debug("Workload schedule from DB: " + str(self.schedule))
        if(self.schedule.find(str(interval)) != -1):
	    reporting.add_test_step("Verification with DB", tvaultconf.PASS)
            LOG.debug("Workload schedule enabled")
        else:
	    reporting.add_test_step("Verification with DB", tvaultconf.FAIL)
            raise Exception("Workload schedule not enabled")
        
        #Cleanup
        #Delete workload
        self.workload_delete(self.wid)
        LOG.debug("Workload deleted successfully")
