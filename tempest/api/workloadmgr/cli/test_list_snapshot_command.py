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
    def test_list_snapshot_command(self):
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
        time.sleep(5)
        
        #Create snapshot
        self.snapshot_id = self.workload_snapshot(self.wid, True, configuration.snapshot_name)
        LOG.debug("Snapshot ID: " + str(self.snapshot_id))
        
        wc = query_data.get_workload_snapshot_status(configuration.snapshot_name,configuration.snapshot_type_full, self.snapshot_id)
        LOG.debug("Workload snapshot status: " + str(wc))
        while (str(wc) != "available" or str(wc)!= "error"):
            time.sleep(5)
            wc = query_data.get_workload_snapshot_status(configuration.snapshot_name, configuration.snapshot_type_full, self.snapshot_id)
            LOG.debug("Workload snapshot status: " + str(wc))
            if (str(wc) == "available"):
                LOG.debug("Workload snapshot successfully completed")
                self.created = True
                break
            else:
                if (str(wc) == "error"):
                    break
        if (self.created == False):
            raise Exception ("Workload snapshot did not get created")
        
        #List snapshots using CLI command
        rc = cli_parser.cli_returncode(command_argument_string.snapshot_list)        
        if rc != 0:
            raise Exception("Command did not execute correctly")
        else:
            LOG.debug("Command executed correctly")
        
        wc = query_data.get_available_snapshots()
        out = cli_parser.cli_output(command_argument_string.snapshot_list)
        if(int(wc) == int(out)):
            LOG.debug("Snapshot list command listed available snapshots correctly")
        else:
            raise Exception ("Snapshot list command did not list available snapshots correctly")
        
        #Cleanup
        #Delete snapshot
        self.snapshot_delete(self.wid, self.snapshot_id)
        LOG.debug("Snapshot deleted successfully")
        
        #Delete workload
        self.workload_delete(self.wid)
        LOG.debug("Workload deleted successfully")
        
        #Delete instance
        self.delete_vm(self.vm_id)
        LOG.debug("Instance deleted successfully")
        
        #Delete corresponding volume
        self.delete_volume(self.volume_id)
        LOG.debug("Volume deleted successfully")