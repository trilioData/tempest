import sys
import os
sys.path.append(os.getcwd())
from tempest.api.workloadmgr import base
from tempest import config
from tempest import test
from oslo_log import log as logging
from tempest import tvaultconf
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
        self.volume_id = self.create_volume(tvaultconf.volume_size,tvaultconf.volume_type)
        LOG.debug("Volume ID: " + str(self.volume_id))
        
        #Attach volume to the instance
        self.attach_volume(self.volume_id, self.vm_id)
        LOG.debug("Volume attached")

        #Create workload
        self.workload_instances.append(self.vm_id)
        self.wid = self.workload_create(self.workload_instances, tvaultconf.parallel, workload_name=tvaultconf.workload_name)
        LOG.debug("Workload ID: " + str(self.wid))
        
        #Launch second instance
        self.vm_id2 = self.create_vm()
        LOG.debug("VM ID2: " + str(self.vm_id2))

        #Create volume
        self.volume_id2 = self.create_volume(tvaultconf.volume_size,tvaultconf.volume_type)
        LOG.debug("Volume ID2: " + str(self.volume_id2))
        
        #Attach volume to the instance
        self.attach_volume(self.volume_id2, self.vm_id2)
        LOG.debug("Volume2 attached")
        
        #Modify workload to add new instance using CLI command        
        workload_modify_command = command_argument_string.workload_modify + str(self.vm_id2) + " --instance instance-id=" + str(self.vm_id) + " " + str(self.wid)
        rc = cli_parser.cli_returncode(workload_modify_command)
        if rc != 0:
            raise Exception("Command did not execute correctly")
        else:
            LOG.debug("Command executed correctly")
            
        self.wait_for_workload_tobe_available(self.wid)        
        workload_vm_count = query_data.get_available_vms_of_workload(self.wid)
        if (workload_vm_count == 2):
            LOG.debug("Workload has been updated successfully")
        else:
            raise Exception ("Workload has not been updated")