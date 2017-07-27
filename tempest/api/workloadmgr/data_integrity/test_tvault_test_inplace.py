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
    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_in_place_restore_cli(self):
	self.total_workloads=1
        self.vms_per_workload=1
        self.volume_size=1
        self.workload_instances = []
        self.workload_volumes = []
        self.workloads = []
        self.full_snapshots = []
        self.restores = []
        self.fingerprint = ""
        self.vm_details_list = []
        self.vms_details = []
        self.floating_ips_list = []
        self.original_fingerprint = ""
        self.vm_list = []
        self.restored_vm_details_list = []
        self.floating_ips_list_after_restore = []
        self.vms_details_after_restore = []
        self.instance_details = []
        self.network_details = []
	volumes = ["/dev/vdb", "/dev/vdc"]
	mount_points = ["mount_data_b", "mount_data_c"]
        self.original_fingerprint = self.create_key_pair(tvaultconf.key_pair_name)
        self.security_group_details = self.create_security_group(tvaultconf.security_group_name)
        security_group_id = self.security_group_details['security_group']['id']
        LOG.debug("security group rules" + str(self.security_group_details['security_group']['rules']))
        flavor_id = self.get_flavor_id(tvaultconf.flavor_name)
        if(flavor_id == 0):
             flavor_id = self.create_flavor(tvaultconf.flavor_name)
        self.original_flavor_conf = self.get_flavor_details(flavor_id)

        for vm in range(0,self.vms_per_workload):
             vm_name = "tempest_test_vm_" + str(vm+1)
             volume_id1 = self.create_volume(self.volume_size,tvaultconf.volume_type)
             volume_id2 = self.create_volume(self.volume_size,tvaultconf.volume_type)
	     vm_id = self.create_vm(vm_name=vm_name ,security_group_id=security_group_id,flavor_id=flavor_id, key_pair=tvaultconf.key_pair_name, vm_cleanup=True)
             self.workload_instances.append(vm_id)
             self.workload_volumes.append(volume_id1)
             self.workload_volumes.append(volume_id2)
             self.attach_volume(volume_id1, vm_id, device=volumes[0])
             self.attach_volume(volume_id2, vm_id, device=volumes[1])

        for id in range(len(self.workload_instances)):
            available_floating_ips = self.get_floating_ips()
            if(len(available_floating_ips) > 0):
                floating_ip = self.get_floating_ips()[0]
            else:
                reporting.add_test_step("Floating ips availability", tvaultconf.FAIL)
                raise Exception("Floating ips not available")
            self.floating_ips_list.append(floating_ip)
            self.set_floating_ip(str(floating_ip), self.workload_instances[id])
	    ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip))
            self.execute_command_disk_create(ssh, str(floating_ip),volumes,mount_points)
            self.execute_command_disk_mount(ssh, str(floating_ip),volumes,mount_points)

        #Fetch instance details before restore
        for id in range(len(self.workload_instances)):
            self.vm_details_list.append(self.get_vm_details(self.workload_instances[id]))
        self.vms_details = self.get_vms_details_list(self.vm_details_list)
        LOG.debug("vm details list before backups" + str( self.vm_details_list))
        LOG.debug("vm details dir before backups" + str( self.vms_details))

	#Fill some data on each of the volumes attached
	self.md5sums_dir_before = self.data_populate_before_backup(self.workload_instances, self.floating_ips_list, 100, 2, mount_points)

        #Create workload and trigger full snapshot
        self.workload_id=self.workload_create(self.workload_instances,tvaultconf.parallel)
        self.snapshot_id=self.workload_snapshot(self.workload_id, True)
        self.wait_for_workload_tobe_available(self.workload_id)
        if(self.getSnapshotStatus(self.workload_id, self.snapshot_id) != "available"):
            reporting.add_test_step("Create full snapshot", tvaultconf.FAIL)	
	    raise Exception("Full Snapshot Failed")
	
	#Fill some more data on each volume attached
	self.md5sums_dir_before = self.data_populate_before_backup(self.workload_instances, self.floating_ips_list, 100, 1, mount_points)
	
	#Create in-place restore with CLI command
        #in_place_restore = command_argument_string.in_place_restore + " --instance instance-id=" +str(self.vm_id)
	command_argument_string  = "workloadmgr snapshot-inplace-restore " + "--display-name " + "test_name_inplace " + "--display-description " + "test_description_inplace " + " --filename " + str(tvaultconf.restore_filename) + " "  + str(self.snapshot_id)
	
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
	#Create Restore.json
	with open(tvaultconf.restore_filename, 'w') as f:
	    f.write(str(json.loads(restore_json)))
        rc = cli_parser.cli_returncode(command_argument_string)
        if rc != 0:
	    reporting.add_test_step("In-Place restore via CLI", tvaultconf.FAIL)
            raise Exception("Command did not execute correctly")
        else:
	    reporting.add_test_step("In-Place restore via CLI", tvaultconf.PASS)
            LOG.debug("Command executed correctly")

	#get restore id from database
	self.restore_id = query_data.get_snapshot_restore_id(self.snapshot_id)	
	self.wait_for_snapshot_tobe_available(self.workload_id, self.snapshot_id)
        
	#get in-place restore status
	if(self.getRestoreStatus(self.workload_id, self.snapshot_id, self.restore_id) == "available"):
            reporting.add_test_step("In-place restore", tvaultconf.PASS)
        else:
            reporting.add_test_step("In-place restore", tvaultconf.FAIL)
            raise Exception("In-place restore failed")	

	md5_sum_after_in_place_restore = self.calculate_md5_after_restore(self.workload_instances, self.floating_ips_list, volumes, mount_points)
	
	if(self.md5sums_dir_before == md5_sum_after_in_place_restore):
            reporting.add_test_step("Md5 Verification", tvaultconf.FAIL)
	    raise Exception("Md5 Verification failed")
        else:
            reporting.add_test_step("Md5 Verification", tvaultconf.PASS)

	
	#Delete restore for snapshot
	self.restored_volumes = self.get_restored_volume_list(self.restore_id)
        self.restore_delete(self.workload_id, self.snapshot_id, self.restore_id)
        LOG.debug("Snapshot Restore deleted successfully")
	
	#Delete restored volumes and volume snapshots
	self.delete_volumes(self.restored_volumes)
