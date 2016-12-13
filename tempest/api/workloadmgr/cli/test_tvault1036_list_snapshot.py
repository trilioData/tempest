import sys
import os
sys.path.append(os.getcwd())
from tempest.api.workloadmgr import base
from tempest import config
from tempest import test
from oslo_log import log as logging
from tempest import tvaultconf
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

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_tvault1036_list_snapshot(self):
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
        time.sleep(5)
        
        #Create snapshot
        self.snapshot_id = self.workload_snapshot(self.wid, True, tvaultconf.snapshot_name)
        LOG.debug("Snapshot ID: " + str(self.snapshot_id))
        
        wc = self.wait_for_snapshot_tobe_available(self.wid,self.snapshot_id)
        if (str(wc) == "available"):
            LOG.debug("Workload snapshot successfully completed")
            self.created = True
        else:
            if (str(wc) == "error"):
                pass
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