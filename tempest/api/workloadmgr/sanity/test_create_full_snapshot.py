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
from tempest import tvaultconf
from tempest import reporting

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        cls.client = cls.os.wlm_client


    def _attached_volume_prerequisite(self, volume_type):
        if(volume_type == "LVM"):
            self.volume_id = self.create_volume(volume_type_id=CONF.volume.volume_type_id_1)
        else:
            self.volume_id = self.create_volume()
	self.vm_id = self.create_vm()
        self.attach_volume(self.volume_id, self.vm_id, device=tvaultconf.volumes_parts[0])


    def _boot_from_volume_prerequisite(self, volume_type):
        if(volume_type == "LVM"):
            self.volume_id = self.create_volume(size=tvaultconf.bootfromvol_vol_size, image_id=CONF.compute.image_ref, volume_type_id=CONF.volume.volume_type_id_1)
        else:
            self.volume_id = self.create_volume(size=tvaultconf.bootfromvol_vol_size, image_id=CONF.compute.image_ref, volume_type_id=CONF.volume.volume_type_id)
	self.set_volume_as_bootable(self.volume_id)
        self.block_mapping_details = [{ "source_type": "volume", 
    		   "delete_on_termination": "false",
    		   "boot_index": 0,
    		   "uuid": self.volume_id,
    		   "destination_type": "volume"}]
        self.vm_id = self.create_vm(image_id="", block_mapping_data=self.block_mapping_details)


    def _create_workload(self, workload_instances):
        self.workload_id=self.workload_create(workload_instances,tvaultconf.parallel, workload_cleanup=False)
        self.wait_for_workload_tobe_available(self.workload_id)
        self.workload_status = self.getWorkloadStatus(self.workload_id)


    def _create_full_snapshot(self):
        self.snapshot_id=self.workload_snapshot(self.workload_id, True, snapshot_cleanup=False)
        self.snapshot_status = self.getSnapshotStatus(self.workload_id, self.snapshot_id)


    def _wait_for_workload(self, workload_id, snapshot_id):
        self.wait_for_workload_tobe_available(workload_id)
        return self.getSnapshotStatus(workload_id, snapshot_id)


    def _trigger_selective_restore(self, workload_instances, workload_id, snapshot_id):
	self.instance_details = []
	int_net_1_name = self.get_net_name(CONF.network.internal_network_id)
        LOG.debug("int_net_1_name" + str(int_net_1_name))
        int_net_1_subnets = self.get_subnet_id(CONF.network.internal_network_id)
        LOG.debug("int_net_1_subnet" + str(int_net_1_subnets))

        #Create instance details for restore.json
        for i in range(len(workload_instances)):
            vm_name = "tempest_test_vm_"+str(i+1)+"_restored"
            temp_instance_data = { 'id': workload_instances[i],
                                   'include': True,
                                   'restore_boot_disk': True,
                                   'name': vm_name,
                                   'vdisks':[]
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
        self.restore_id=self.snapshot_selective_restore(workload_id, snapshot_id,restore_name=tvaultconf.restore_name,
                                                        instance_details=self.instance_details, network_details=self.network_details)
	return self.restore_id


    def _delete_restore(self, workload_id, snapshot_id, restore_id):
	return self.restore_delete(workload_id, snapshot_id, restore_id)


    def _delete_snapshot(self, workload_id, snapshot_id):
        return self.snapshot_delete(workload_id, snapshot_id)


    def _delete_workload(self, workload_id):
        return self.workload_delete(workload_id)


    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_create_full_snapshot(self):
	try:
	    result_json = {}
            for test in tvaultconf.enabled_tests:
                result_json[test] = {}
            LOG.debug("Result json: " + str(result_json))

            for k in result_json.keys():
	        result_json[k]['result'] = {}
                if(k.find("Attach") != -1):
                   if(k.find("Ceph") != -1):
                       self._attached_volume_prerequisite("Ceph")
                   else:
                       self._attached_volume_prerequisite("LVM")
		elif(k.find("Boot") != -1):
                   if(k.find("Ceph") != -1):
                       self._boot_from_volume_prerequisite("Ceph")
                   else:
                       self._boot_from_volume_prerequisite("LVM")

                result_json[k]['instances'] = self.vm_id
                result_json[k]['volumes'] = self.volume_id
                self._create_workload([self.vm_id])
                result_json[k]['workload'] = self.workload_id
                result_json[k]['workload_status'] = self.workload_status
                if(self.workload_status == "available"):
                    result_json[k]['result']['Create_Workload'] = tvaultconf.PASS
                else:
                    result_json[k]['result']['Create_Workload'] = tvaultconf.FAIL
                    continue

                self._create_full_snapshot()
                result_json[k]['snapshot'] = self.snapshot_id
                result_json[k]['snapshot_status'] = self.snapshot_status
            LOG.debug("Result json after trigger full snapshot: " + str(result_json))

            for k in result_json.keys():
		if('snapshot_status' in result_json[k].keys()):
                    result_json[k]['snapshot_status'] = self._wait_for_workload(result_json[k]['workload'], result_json[k]['snapshot'])
		    result_json[k]['workload_status'] = self.getWorkloadStatus(result_json[k]['workload'])
                    if(result_json[k]['snapshot_status'] == "available"):
                        result_json[k]['result']['Create_Snapshot'] = tvaultconf.PASS
                    else:
		        result_json[k]['snapshot_error_msg'] = (self.getSnapshotDetails(result_json[k]['workload'], result_json[k]['snapshot']))['error_msg']
                        result_json[k]['result']['Create_Snapshot'] = tvaultconf.FAIL
            LOG.debug("Result json after snapshot complete: " + str(result_json))

	    for k in result_json.keys():
	        if('snapshot_status' in result_json[k].keys() and result_json[k]['snapshot_status'] == "available"):
	 	    self.restore_id = self._trigger_selective_restore([result_json[k]['instances']], result_json[k]['workload'], result_json[k]['snapshot'])
		    result_json[k]['restore'] = self.restore_id
	    LOG.debug("Result json after trigger selective restore: " + str(result_json))

	    for k in result_json.keys():
                if('restore' in result_json[k].keys()):
                    result_json[k]['snapshot_status'] = self._wait_for_workload(result_json[k]['workload'], result_json[k]['snapshot'])
                    result_json[k]['workload_status'] = self.getWorkloadStatus(result_json[k]['workload'])
		    result_json[k]['restore_status'] = self.getRestoreStatus(result_json[k]['workload'], result_json[k]['snapshot'], result_json[k]['restore'])
		    if(result_json[k]['restore_status'] == "available"):
                        result_json[k]['result']['Selective_Restore'] = tvaultconf.PASS
                    else:
                        result_json[k]['restore_error_msg'] = (self.getRestoreDetails(result_json[k]['restore']))['error_msg']
                        result_json[k]['result']['Selective_Restore'] = tvaultconf.FAIL
            LOG.debug("Result json after selective restore complete: " + str(result_json))

	    for k in result_json.keys():
               if('restore_status' in result_json[k].keys()):
                   result_json[k]['snapshot_status'] = self._wait_for_workload(result_json[k]['workload'], result_json[k]['snapshot'])
                   result_json[k]['workload_status'] = self.getWorkloadStatus(result_json[k]['workload'])
		   result_json[k]['restore_status'] = self.getRestoreStatus(result_json[k]['workload'], result_json[k]['snapshot'], result_json[k]['restore'])
                   if(result_json[k]['workload_status'] == "available" and result_json[k]['restore_status'] in ("available", "error")):
                       result_json[k]['restore_delete_response'] = self._delete_restore(result_json[k]['workload'], result_json[k]['snapshot'], result_json[k]['restore'])
                       #if(result_json[k]['restore_delete_response']):
                       #    result_json[k]['result']['Delete_Restore'] = tvaultconf.PASS
                       #else:
                       #    result_json[k]['result']['Delete_Restore'] = tvaultconf.FAIL
            LOG.debug("Result json after delete restore: " + str(result_json))


            for k in result_json.keys():
               if('snapshot_status' in result_json[k].keys()):
		   result_json[k]['snapshot_status'] = self._wait_for_workload(result_json[k]['workload'], result_json[k]['snapshot'])
		   result_json[k]['workload_status'] = self.getWorkloadStatus(result_json[k]['workload'])
	           if(result_json[k]['workload_status'] == "available" and result_json[k]['snapshot_status'] in ("available", "error")):
	               result_json[k]['snapshot_delete_response'] = self._delete_snapshot(result_json[k]['workload'], result_json[k]['snapshot'])
                       #if(result_json[k]['snapshot_delete_response']):
                       #    result_json[k]['result']['Delete_Snapshot'] = tvaultconf.PASS
                       #else:
                       #    result_json[k]['result']['Delete_Snapshot'] = tvaultconf.FAIL
            LOG.debug("Result json after delete snapshot: " + str(result_json))

            for k in result_json.keys():
               if('workload_status' in result_json[k].keys()):
		   result_json[k]['workload_status'] = self.getWorkloadStatus(result_json[k]['workload'])
	           if(result_json[k]['workload_status'] in ("available", "error")):
	               result_json[k]['workload_delete_response'] = self._delete_workload(result_json[k]['workload'])
                       #if(result_json[k]['workload_delete_response']):
                       #    result_json[k]['result']['Delete_Workload'] = tvaultconf.PASS
                       #else:
                       #    result_json[k]['result']['Delete_Workload'] = tvaultconf.FAIL
            LOG.debug("Result json after delete workload: " + str(result_json))

	except Exception as e:
	    LOG.error("Exception: " + str(e))

	finally:
	    #Add results to sanity report
	    LOG.debug("Finally Result json: " + str(result_json))
            for k,v in result_json.items():
	 	if(('result' in v.keys()) and (len(v['result'].keys()) > 0)):
	            for k1 in reversed(v['result'].keys()):
                        reporting.add_sanity_results(k1+"_"+k, v['result'][k1])

