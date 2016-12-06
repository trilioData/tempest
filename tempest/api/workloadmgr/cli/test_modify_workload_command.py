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
    def test_modify_workload_command(self):
        #Prerequisites
        self.created = False
        self.workload_instances = []
        #Launch instance
        self.vm_id = self.create_vm()
        LOG.debug("VM ID: " + str(self.vm_id))

        #Create volume
        self.volume_id = self.create_volume(configuration.volume_size,tvaultconf.volume_type)
        LOG.debug("Volume ID: " + str(self.volume_id))
        
        #Attach volume to the instance
        self.attach_volume(self.volume_id, self.vm_id)
        LOG.debug("Volume attached")

        #Create workload
        self.workload_instances.append(self.vm_id)
        self.wid = self.workload_create(self.workload_instances, tvaultconf.parallel, workload_name=configuration.workload_name)
        LOG.debug("Workload ID: " + str(self.wid))
        
        #Modify workload name using CLI command        
        workload_modify_name_command = command_argument_string.workload_modify_name + configuration.workload_modify_name + " " +str(self.wid)
        rc = cli_parser.cli_returncode(workload_modify_name_command)
        if rc != 0:
            raise Exception("Command did not execute correctly")
        else:
            LOG.debug("Command executed correctly")
        workload_name = query_data.get_workload_display_name(self.wid)
        if (workload_name) == configuration.workload_modify_name:
            LOG.debug("Workload name has been changed successfully")
        else:
            raise Exception ("Workload name has not been changed!!!")

        #Modify workload description using CLI command
        workload_modify_description_command = command_argument_string.workload_modify_description + configuration.workload_modify_description + " " + str(self.wid)
        cli_parser.cli_returncode(workload_modify_description_command)
        if rc != 0:
            raise Exception("Command did not execute correctly")
        else:
            LOG.debug("Command executed correctly")            
        workload_description = query_data.get_workload_display_description(self.wid)
        if (workload_description) == configuration.workload_modify_description:
            LOG.debug("Workload description has been changed successfully")
        else:
            raise Exception("Workload description has not been changed")
        
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