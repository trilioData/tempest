# Copyright 2014 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from tempest.api.workloadmgr import base
from tempest import config
from tempest import test
from tempest import tvaultconf
import json
import sys
from tempest import api
from oslo_log import log as logging
from tempest.common import waiters
from tempest import tvaultconf, reporting
import time

from tempest import command_argument_string
from tempest.util import cli_parser, query_data
import collections
from tempest.api.workloadmgr.cli.config import command_argument_string
from tempest.api.workloadmgr.cli.util import cli_parser, query_data

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
	reporting.add_test_script(str(__name__))
    @test.pre_req({'type':'inplace'})
    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_in_place_restore_cli(self):
	try:

	    volumes = ["/dev/vdb", "/dev/vdc"]
            mount_points = ["mount_data_b", "mount_data_c"]	

	    #Fill some more data on each volume attached
            tree = lambda: collections.defaultdict(tree)
            self.md5sums_dir_before = tree()
            for floating_ip in self.floating_ips_list:
                for mount_point in mount_points:
	    	    ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip))
                    self.addCustomSizedfilesOnLinux(ssh, mount_point, 1)
	    	    ssh.close()
	        for mount_point in mount_points:
	    	    ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip))
                    self.md5sums_dir_before[str(floating_ip)][str(mount_point)] = self.calculatemmd5checksum(ssh, mount_point)
	      	    ssh.close()
	    
	    LOG.debug("md5sums_dir_before" + str(self.md5sums_dir_before))	
	    #Create in-place restore with CLI command
	    restore_command  = command_argument_string.inplace_restore + str(tvaultconf.restore_filename) + " "  + str(self.snapshot_id)
	    
	    LOG.debug("inplace restore cli command: " + str(restore_command) )
	    #Restore.json with only volume 2 excluded
            restore_json = json.dumps({
	    'openstack': {
	    	'instances': [{
	    		'restore_boot_disk': True,
	    		'include': True,
	    		'id': self.workload_instances[0],
	    		'vdisks': [{
	    			'restore_cinder_volme': True,
	    			'id': self.workload_volumes[0],
	    		},
	    		{
	    			'restore_cinder_volme': False,
	    			'id': self.workload_volumes[1],
	    			
	    		}]
	    	}],
	    	'networks_mapping': {
	    		'networks': []
	    	}
	    },
	    'restore_type': 'inplace',
	    'type': 'openstack'
 })
	    LOG.debug("restore.json for inplace restore: " + str(restore_json))
	    #Create Restore.json
	    with open(tvaultconf.restore_filename, 'w') as f:
	        f.write(str(json.loads(restore_json)))
            rc = cli_parser.cli_returncode(restore_command)
            if rc != 0:
	        reporting.add_test_step("Triggering In-Place restore via CLI", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
	        reporting.add_test_step("Triggering In-Place restore via CLI", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

	    #get restore id from database
	    self.restore_id = query_data.get_snapshot_restore_id(self.snapshot_id)	
	    self.wait_for_snapshot_tobe_available(self.workload_id, self.snapshot_id)
            
	    #get in-place restore status
	    if(self.getRestoreStatus(self.workload_id, self.snapshot_id, self.restore_id) == "available"):
                reporting.add_test_step("In-place restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("In-place restore", tvaultconf.FAIL)
		reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("In-place restore failed")	
	    
	    # calculate md5 after inplace restore
            tree = lambda: collections.defaultdict(tree)
            md5_sum_after_in_place_restore = tree()
            for floating_ip in self.floating_ips_list:
                for mount_point in mount_points:
	    	    ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip))
                    md5_sum_after_in_place_restore[str(floating_ip)][str(mount_point)] = self.calculatemmd5checksum(ssh, mount_point)
	    	    ssh.close()
	    LOG.debug("md5_sum_after_in_place_restore" + str(md5_sum_after_in_place_restore))
	    
	    if(self.md5sums_dir_before == md5_sum_after_in_place_restore):
                reporting.add_test_step("Md5 Verification", tvaultconf.FAIL)
		reporting.set_test_script_status(tvaultconf.FAIL)
	        raise Exception("Md5 Verification failed")
            else:
                reporting.add_test_step("Md5 Verification", tvaultconf.PASS)

	    
	    #Delete restore for snapshot
	    self.restored_volumes = self.get_restored_volume_list(self.restore_id)
	    if tvaultconf.cleanup==True: 
                self.restore_delete(self.workload_id, self.snapshot_id, self.restore_id)
                LOG.debug("Snapshot Restore deleted successfully")
	        
	        #Delete restored volumes and volume snapshots
	        self.delete_volumes(self.restored_volumes)

	    reporting.test_case_to_write()

	except Exception as e:
	    LOG.error("Exception: " + str(e))
	    reporting.set_test_script_status(tvaultconf.FAIL)
	    reporting.test_case_to_write()
