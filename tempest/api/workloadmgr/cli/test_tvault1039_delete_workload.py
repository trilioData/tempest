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
    def test_tvault1039_delete_workload(self):
        #Prerequisites
        self.deleted = False
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
        self.wid = self.workload_create(self.workload_instances, tvaultconf.parallel, workload_name=tvaultconf.workload_name, workload_cleanup=False)
        LOG.debug("Workload ID: " + str(self.wid))
        time.sleep(5)
        
        #Delete workload from CLI command
        rc = cli_parser.cli_returncode(command_argument_string.workload_delete)
        if rc != 0:
            raise Exception("Command did not execute correctly")
        else:
            LOG.debug("Command executed correctly")
        
        wc = query_data.get_deleted_workload(tvaultconf.workload_name)
        LOG.debug("Workload status: " + str(wc))
        while (str(wc) != "deleted"):
            time.sleep(5)
            wc = query_data.get_deleted_workload(tvaultconf.workload_name)
            LOG.debug("Workload status: " + str(wc))
            if (str(wc) == "deleted"):
                LOG.debug("Workload successfully deleted")
                self.deleted = True
                break
        if (self.deleted == False):
            raise Exception ("Workload did not get deleted")