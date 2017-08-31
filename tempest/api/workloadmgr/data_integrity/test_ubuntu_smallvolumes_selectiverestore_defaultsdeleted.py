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
import json
import sys
from tempest import api
from oslo_log import log as logging
from tempest.common import waiters
from tempest import tvaultconf, reporting
import time
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
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c2')
    def test_ubuntu_smallvolumes_selectiverestore_defaultsdeleted(self):
	try:
            self.total_workloads=1
            self.vms_per_workload=2
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
	    self.original_fingerprint = self.create_key_pair(tvaultconf.key_pair_name)
            self.security_group_details = self.create_security_group(tvaultconf.security_group_name, secgrp_cleanup=False)
            security_group_id = self.security_group_details['security_group']['id']
            LOG.debug("security group rules" + str(self.security_group_details['security_group']['rules']))
            flavor_id = self.get_flavor_id(tvaultconf.flavor_name)
	    if(flavor_id == 0):
	         flavor_id = self.create_flavor(tvaultconf.flavor_name, flavor_cleanup=False)
	    self.original_flavor_conf = self.get_flavor_details(flavor_id)

            for vm in range(0,self.vms_per_workload):
                 vm_name = "tempest_test_vm_" + str(vm+1)
	         volume_id1 = self.create_volume(self.volume_size,tvaultconf.volume_type)
                 volume_id2 = self.create_volume(self.volume_size,tvaultconf.volume_type)
                 vm_id = self.create_vm(vm_name=vm_name ,security_group_id=security_group_id,flavor_id=flavor_id, key_pair=tvaultconf.key_pair_name, vm_cleanup=False)
                 self.workload_instances.append(vm_id)
                 self.workload_volumes.append(volume_id1)
                 self.workload_volumes.append(volume_id2)
                 self.attach_volume(volume_id1, vm_id, device=volumes[0])
                 self.attach_volume(volume_id2, vm_id,device=volumes[1])


	    #Fetch instance details before restore
            for id in range(len(self.workload_instances)):
                self.vm_details_list.append(self.get_vm_details(self.workload_instances[id]))
            self.vms_details = self.get_vms_details_list(self.vm_details_list)
            LOG.debug("vm details list before backups" + str( self.vm_details_list))
            LOG.debug("vm details dir before backups" + str( self.vms_details))

	    #Create workload and trigger full snapshot
            self.workload_id=self.workload_create(self.workload_instances,tvaultconf.parallel)
            self.snapshot_id=self.workload_snapshot(self.workload_id, True)
            self.wait_for_workload_tobe_available(self.workload_id)
	    if(self.getSnapshotStatus(self.workload_id, self.snapshot_id) != "available"):
	        reporting.add_test_step("Create full snapshot", tvaultconf.FAIL)
	    #self.workload_reset(self.workload_id)
            time.sleep(10)
            
	    self.delete_vms(self.workload_instances)
	    self.delete_volumes(self.workload_volumes)
            self.delete_key_pair(tvaultconf.key_pair_name)
            self.delete_security_group(security_group_id)
            self.delete_flavor(flavor_id)

            int_net_1_name = self.get_net_name(CONF.network.internal_network_id)
            LOG.debug("int_net_1_name" + str(int_net_1_name))
            int_net_1_subnets = self.get_subnet_id(CONF.network.internal_network_id)
            LOG.debug("int_net_1_subnet" + str(int_net_1_subnets))

	    #Create instance details for restore.json
	    temp_vdisks_data = []
	    for i in range(len(self.workload_instances)):
	        flag=i+i
	    		
	        temp_vdisks_data.append ([{'id':self.workload_volumes[flag],
                                     'availability_zone':CONF.volume.volume_availability_zone,
	    	     	         'new_volume_type':CONF.volume.volume_type
                                    },
                                    {'id':self.workload_volumes[flag+1],
                                     'availability_zone':CONF.volume.volume_availability_zone,
	    		         'new_volume_type':CONF.volume.volume_type
                                    }]
	    		       )

            LOG.debug("Vdisks details for restore"+str(temp_vdisks_data))

	    for i in range(len(self.workload_instances)):
	        vm_name = "tempest_test_vm_"+str(i+1)+"_restored"
	        temp_instance_data = { 'id': self.workload_instances[i],
	    			   'availability_zone':CONF.compute.vm_availability_zone, 
	    			   'include': True,
	    			   'restore_boot_disk': True,
	    			   'name': vm_name,
	    			   'vdisks':temp_vdisks_data[i]
	    			 }
	        self.instance_details.append(temp_instance_data)
	    LOG.debug("Instance details for restore: " + str(self.instance_details))
	    
	    #Create network details for restore.json
	    snapshot_network = { 'name': int_net_1_name,
	    		     'id': CONF.network.internal_network_id,
	    		     'subnet': { 'id': int_net_1_subnets }
	    		   }
	    target_network = { 'name': int_net_1_name,
                               'id': CONF.network.internal_network_id,
                               'subnet': { 'id': int_net_1_subnets }
                             }
	    self.network_details = [ { 'snapshot_network': snapshot_network,
	    			   'target_network': target_network } ]
	    LOG.debug("Network details for restore: " + str(self.network_details))

	    #Trigger selective restore
            self.restore_id=self.snapshot_selective_restore(self.workload_id, self.snapshot_id,restore_name=tvaultconf.restore_name,
                                                            instance_details=self.instance_details, network_details=self.network_details, sec_group_cleanup = True)
            self.wait_for_snapshot_tobe_available(self.workload_id, self.snapshot_id)
	    if(self.getRestoreStatus(self.workload_id, self.snapshot_id, self.restore_id) == "available"):
	        reporting.add_test_step("Selective restore", tvaultconf.PASS)
	    else:
	        reporting.add_test_step("Selective restore", tvaultconf.FAIL)
		reporting.set_test_script_status(tvaultconf.FAIL)
	        raise Exception("Selective restore failed")

            #Fetch instance details after restore
            self.restored_vm_details_list = []
            self.vm_list  =  self.get_restored_vm_list(self.restore_id)
            LOG.debug("Restored vms : " + str (self.vm_list))

            for id in range(len(self.vm_list)):
                self.restored_vm_details_list.append(self.get_vm_details(self.vm_list[id]))
            LOG.debug("Restored vm details list: " + str(self.restored_vm_details_list))
	    
            self.vms_details_after_restore = self.get_vms_details_list(self.restored_vm_details_list)
	    LOG.debug("VM details after restore: " + str(self.vms_details_after_restore))

	    #Compare the data before and after restore
	    for i in range(len(self.vms_details_after_restore)):

	        if(self.vms_details_after_restore[i]['network_name'] == int_net_1_name):
	    	    reporting.add_test_step("Network verification for instance-" + str(i+1), tvaultconf.PASS)
	        else:
	    	    LOG.error("Expected network: " + str(int_net_1_name))
                    LOG.error("Restored network: " + str(self.vms_details_after_restore[i]['network_name']))
	    	    reporting.add_test_step("Network verification for instance-" + str(i+1), tvaultconf.FAIL)
		    reporting.set_test_script_status(tvaultconf.FAIL)

	        if(self.get_key_pair_details(self.vms_details_after_restore[i]['keypair']) == self.original_fingerprint):
	    	    reporting.add_test_step("Keypair verification for instance-" + str(i+1), tvaultconf.PASS)
	        else:
	    	    LOG.error("Original keypair details: " + str(self.original_fingerprint))
                    LOG.error("Restored keypair details: " + str(self.get_key_pair_details(self.vms_details_after_restore[i]['keypair'])))
	    	    reporting.add_test_step("Keypair verification for instance-" + str(i+1), tvaultconf.FAIL)
		    reporting.set_test_script_status(tvaultconf.FAIL)

	        if(self.get_flavor_details(self.vms_details_after_restore[i]['flavor_id']) == self.original_flavor_conf):
	    	    reporting.add_test_step("Flavor verification for instance-" + str(i+1), tvaultconf.PASS)
	        else:
	    	    LOG.error("Original flavor details: " + str(self.original_flavor_conf))
	    	    LOG.error("Restored flavor details: " + str(self.get_flavor_details(self.vms_details_after_restore[i]['flavor_id'])))
	    	    reporting.add_test_step("Flavor verification for instance-" + str(i+1), tvaultconf.FAIL)
		    reporting.set_test_script_status(tvaultconf.FAIL)

	    reporting.test_case_to_write()

	except Exception as e:
	    LOG.error("Exception: " + str(e))
	    reporting.set_test_script_status(tvaultconf.FAIL)
	    reporting.test_case_to_write()
