import sys
import os
sys.path.append(os.getcwd())
from tempest.api.workloadmgr import base
from tempest import config
from tempest import test
from oslo_log import log as logging
from tempest import tvaultconf
import time
from tempest.api.workloadmgr.cli.config import command_argument_string, configuration
from tempest.api.workloadmgr.cli.util import cli_parser, query_data

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
    def test_create_workload_command(self):
        #Prerequisites
        self.created = False
        #Launch instance
        self.vm_id = self.create_vm()
        LOG.debug("VM ID: " + str(self.vm_id))

        #Create volume
        self.volume_id = self.create_volume(configuration.volume_size,tvaultconf.volume_type)
        LOG.debug("Volume ID: " + str(self.volume_id))
        
        #Attach volume to the instance
        self.attach_volume(self.volume_id, self.vm_id)
        LOG.debug("Volume attached")

        #Create workload with CLI command
        workload_create = command_argument_string.workload_create + " --instance instance-id=" +str(self.vm_id)
        rc = cli_parser.cli_returncode(workload_create)
        if rc != 0:
            raise Exception("Command did not execute correctly")
        else:
            LOG.debug("Command executed correctly")
        
        wc = query_data.get_workload_status(configuration.workload_name)
        LOG.debug("Workload status: " + str(wc))
        while (str(wc) != "available" or str(wc)!= "error"):
            time.sleep(10)
            wc = query_data.get_workload_status(configuration.workload_name)
            LOG.debug("Workload status: " + str(wc))
            if (str(wc) == "available"):
                LOG.debug("Workload successfully created")
                self.created = True
                break
            else:
                if (str(wc) == "error"):
                    break
        if (self.created == False):
            raise Exception ("Workload did not get created!!!")
        
        self.wid = query_data.get_workload_id(configuration.workload_name)
        LOG.debug("Workload ID: " + str(self.wid))
        
        #Cleanup
        #Delete workload
        self.workload_delete(self.wid)
        LOG.debug("Workload deleted successfully")
        
        #Delete instance
        self.delete_vm(self.vm_id)
        LOG.debug("Instance deleted successfully")
        
        #Delete corresponding volume
        self.delete_volume(self.volume_id)
        LOG.debug("Volume deleted successfully")