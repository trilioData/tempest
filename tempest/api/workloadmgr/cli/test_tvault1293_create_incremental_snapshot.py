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
    def test_tvault1293_create_incremental_snapshot(self):
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
                
        #Create full snapshot
        self.snapshot_id = self.workload_snapshot(self.wid, True, tvaultconf.snapshot_name)
        LOG.debug("Full Snapshot ID: " + str(self.snapshot_id))
        
        wc = self.wait_for_snapshot_tobe_available(self.wid,self.snapshot_id)
        if (str(wc) == "available"):
            LOG.debug("Workload full snapshot successfully completed")
        else:
            if (str(wc) == "error"):
                raise Exception ("Workload full snapshot did not get created")
        
        #Create incremental snapshot using CLI command
        create_snapshot = command_argument_string.incr_snapshot_create + self.wid
        LOG.debug("Create snapshot command: " + str(create_snapshot))
        rc = cli_parser.cli_returncode(create_snapshot)
        if rc != 0:
            raise Exception("Command did not execute correctly")
        else:
            LOG.debug("Command executed correctly")
               
        self.incr_snapshot_id = query_data.get_inprogress_snapshot_id(self.wid)
        LOG.debug("Incremental Snapshot ID: " + str(self.incr_snapshot_id))
        
        #Wait for incremental snapshot to complete
        wc = self.wait_for_snapshot_tobe_available(self.wid, self.incr_snapshot_id)
        if (str(wc) == "available"):
            LOG.debug("Workload incremental snapshot successfully completed")
            self.created = True
        else:
            if (str(wc) == "error"):
                raise Exception ("Workload incremental snapshot did not get created")
        if (self.created == False):
            raise Exception ("Workload incremental snapshot did not get created")
        
        #Cleanup
        #Delete snapshot
        self.snapshot_delete(self.wid, self.incr_snapshot_id)
        LOG.debug("Incremental Snapshot deleted successfully")