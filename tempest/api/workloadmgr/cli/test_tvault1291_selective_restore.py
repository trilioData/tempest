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

class RestoreTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(RestoreTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
	reporting.add_test_script(str(__name__))

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_tvault1291_selective_restore(self):
        #Prerequisites
        self.created = False
        self.workload_instances = []
        
        #Launch instance
        self.vm_id = self.create_vm(vm_cleanup=False)
        LOG.debug("VM ID: " + str(self.vm_id))

        #Create volume
        self.volume_id = self.create_volume(tvaultconf.volume_size,tvaultconf.volume_type, volume_cleanup=False)
        LOG.debug("Volume ID: " + str(self.volume_id))
        
        #Attach volume to the instance
        self.attach_volume(self.volume_id, self.vm_id, attach_cleanup=False)
        LOG.debug("Volume attached")

        #Create workload
        self.workload_instances.append(self.vm_id)
        self.wid = self.workload_create(self.workload_instances, tvaultconf.parallel, workload_name=tvaultconf.workload_name)
        LOG.debug("Workload ID: " + str(self.wid))
        time.sleep(5)
        
        #Create snapshot
        self.snapshot_id = self.workload_snapshot(self.wid, True, tvaultconf.snapshot_name)
        LOG.debug("Snapshot ID: " + str(self.snapshot_id))
        
        #Wait till snapshot is complete
        wc = query_data.get_workload_snapshot_status(tvaultconf.snapshot_name,tvaultconf.snapshot_type_full, self.snapshot_id)
        LOG.debug("Workload snapshot status: " + str(wc))
        while (str(wc) != "available" or str(wc)!= "error"):
            time.sleep(5)
            wc = query_data.get_workload_snapshot_status(tvaultconf.snapshot_name, tvaultconf.snapshot_type_full, self.snapshot_id)
            LOG.debug("Workload snapshot status: " + str(wc))
            if (str(wc) == "available"):
                LOG.debug("Workload snapshot successfully completed")
                self.created = True
                break
            else:
                if (str(wc) == "error"):
                    break
        if (self.created == False):
	    reporting.add_test_step("Create full snapshot", tvaultconf.FAIL)
            raise Exception ("Workload snapshot did not get created")
        
        #Delete instance
        self.delete_vm(self.vm_id)
        LOG.debug("Instance deleted successfully")
        
        #Delete corresponding volume
        self.delete_volume(self.volume_id)
        LOG.debug("Volume deleted successfully")
        
        #Create selective restore using CLI command
        restore_command = command_argument_string.selective_restore + " " + self.snapshot_id
        rc = cli_parser.cli_returncode(restore_command)
        if rc != 0:
	    reporting.add_test_step("Execute snapshot-selective-restore command", tvaultconf.FAIL)
            raise Exception("Command did not execute correctly")
        else:
	    reporting.add_test_step("Execute snapshot-selective-restore command", tvaultconf.PASS)
            LOG.debug("Command executed correctly")
            
        wc = query_data.get_snapshot_restore_status(tvaultconf.selective_restore_name,self.snapshot_id)
        LOG.debug("Snapshot restore status: " + str(wc))
        while (str(wc) != "available" or str(wc) != "error" or str(wc) != "None"):
            time.sleep(5)
            wc = query_data.get_snapshot_restore_status(tvaultconf.selective_restore_name, self.snapshot_id)
            LOG.debug("Snapshot restore status: " + str(wc))
            if (str(wc) == "available"):
		reporting.add_test_step("Snapshot selective restore", tvaultconf.PASS)
                LOG.debug("Snapshot Restore successfully completed")
                self.created = True
                break
            elif (str(wc) == "error" or str(wc) == "None"):
                    break
        if (self.created == False):
	    reporting.add_test_step("Snapshot selective restore", tvaultconf.FAIL)
            raise Exception ("Snapshot Restore did not get created")
        
        self.restore_id = query_data.get_snapshot_restore_id(self.snapshot_id)
        LOG.debug("Restore ID: " + str(self.restore_id))
        
        self.restore_vm_id = self.get_restored_vm_list(self.restore_id)
        LOG.debug("Restore VM ID: " + str(self.restore_vm_id))
        
        self.restore_volume_id = self.get_restored_volume_list(self.restore_id)
        LOG.debug("Restore Volume ID: " + str(self.restore_volume_id))
        
        #Cleanup
        #Delete restore for snapshot
        self.restore_delete(self.wid, self.snapshot_id, self.restore_id)
        LOG.debug("Snapshot Restore deleted successfully")
        
        #Delete restored VM instance and volume
        self.delete_restored_vms(self.restore_vm_id, self.restore_volume_id)
        LOG.debug("Restored VM deleted successfully")
