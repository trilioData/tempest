import sys
import os
sys.path.append(os.getcwd())
from tempest.api.workloadmgr import base
from tempest import config
from tempest import test
from oslo_log import log as logging
from tempest import tvaultconf
from tempest import reporting
import time
import json
from tempest.api.workloadmgr.cli.config import command_argument_string
from tempest.api.workloadmgr.cli.util import cli_parser
from tempest.api.workloadmgr.cli.util import query_data

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
	try:
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
            self.wait_for_workload_tobe_available(self.wid) 
	    if(self.getSnapshotStatus(self.wid, self.snapshot_id) != "available"):
                reporting.add_test_step("Create snapshot", tvaultconf.FAIL)
       	        raise Exception("Create snapshot failed") 

            #Delete instance
            self.delete_vm(self.vm_id)
            LOG.debug("Instance deleted successfully")
        
            #Delete corresponding volume
            self.delete_volume(self.volume_id)
            LOG.debug("Volume deleted successfully")

    	    #Create restore.json file
 	    int_net_1_name = self.get_net_name(CONF.network.internal_network_id)
            LOG.debug("int_net_1_name" + str(int_net_1_name))
            int_net_1_subnets = self.get_subnet_id(CONF.network.internal_network_id)
            LOG.debug("int_net_1_subnet" + str(int_net_1_subnets))
            snapshot_network = { 'name': int_net_1_name,
                                 'id': CONF.network.internal_network_id,
                                 'subnet': { 'id': int_net_1_subnets }
                               }
            target_network = { 'name': int_net_1_name,
                               'id': CONF.network.internal_network_id,
                               'subnet': { 'id': int_net_1_subnets }
                             }
	    restore_json = json.dumps({
	    'openstack': {
		'instances': [{
			'include': True,
			'id': self.vm_id,
			'availability_zone': CONF.compute.availability_zone,
			'vdisks': [{ 'id': self.volume_id,
                              'availability_zone':CONF.volume.availability_zone,
                              'new_volume_type':CONF.volume.volume_type
                           	   }]
			       }],
		'networks_mapping': {
			'networks': [{ 'snapshot_network': snapshot_network,
                                       'target_network': target_network }]
		}
	    },
	    'restore_type': 'selective',
	    'oneclickrestore': 'False',
	    'type': 'openstack'
        })

	    #Create Restore.json
	    with open(tvaultconf.restore_filename, 'w') as f:
	        f.write(str(json.loads(restore_json)))
        
            #Create selective restore using CLI command
            restore_command = command_argument_string.selective_restore + " " + self.snapshot_id
            rc = cli_parser.cli_returncode(restore_command)
            if rc != 0:
	        reporting.add_test_step("Execute snapshot-selective-restore command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
	        reporting.add_test_step("Execute snapshot-selective-restore command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

	    self.restore_id = query_data.get_snapshot_restore_id(self.snapshot_id)
            LOG.debug("Restore ID: " + str(self.restore_id))
            self.wait_for_workload_tobe_available(self.wid)
            if(self.getRestoreStatus(self.wid, self.snapshot_id, self.restore_id) != "available"):
                reporting.add_test_step("Selective restore", tvaultconf.FAIL)
                raise Exception("Selective restore failed")    
	    else:
	        reporting.add_test_step("Selective restore", tvaultconf.PASS)
        
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
	    reporting.test_case_to_write()

	except Exception as e:
	    LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
	    
