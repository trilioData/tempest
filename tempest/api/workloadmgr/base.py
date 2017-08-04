# Copyright 2012 OpenStack Foundation
# All Rights Reserved.
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

import time,json
import paramiko
import os, stat

from oslo_log import log as logging
from tempest import config
import tempest.test
from tempest.common import waiters
from oslo_config import cfg
from tempest_lib import exceptions as lib_exc
from datetime import datetime, timedelta
from tempest import tvaultconf

CONF = config.CONF
LOG = logging.getLogger(__name__)

#Unused imports
#import unittest
#from testtools import testcase
#from tempest import api
#from tempest.common import compute
#from random import choice
#from string import ascii_lowercase


class BaseWorkloadmgrTest(tempest.test.BaseTestCase):

    _api_version = 2
    force_tenant_isolation = False
    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(BaseWorkloadmgrTest, cls).setup_clients()
        cls.subnets_client = cls.os.subnets_client
        cls.wlm_client = cls.os.wlm_client
        cls.servers_client = cls.os.servers_client
        cls.server_groups_client = cls.os.server_groups_client
        cls.flavors_client = cls.os.flavors_client
        cls.images_client = cls.os.images_client
        cls.extensions_client = cls.os.extensions_client
        cls.floating_ip_pools_client = cls.os.floating_ip_pools_client
        cls.floating_ips_client = cls.os.floating_ips_client
        cls.keypairs_client = cls.os.keypairs_client
        cls.security_group_rules_client = cls.os.security_group_rules_client
        cls.security_groups_client = cls.os.security_groups_client
        cls.quotas_client = cls.os.quotas_client
        cls.quota_classes_client = cls.os.quota_classes_client
        cls.compute_networks_client = cls.os.compute_networks_client
        cls.limits_client = cls.os.limits_client
        cls.volumes_extensions_client = cls.os.volumes_extensions_client
        cls.snapshots_extensions_client = cls.os.snapshots_extensions_client
        cls.network_client = cls.os.network_client
        cls.interfaces_client = cls.os.interfaces_client
        cls.fixed_ips_client = cls.os.fixed_ips_client
        cls.availability_zone_client = cls.os.availability_zone_client
        cls.agents_client = cls.os.agents_client
        cls.aggregates_client = cls.os.aggregates_client
        cls.services_client = cls.os.services_client
        cls.instance_usages_audit_log_client = (
            cls.os.instance_usages_audit_log_client)
        cls.hypervisor_client = cls.os.hypervisor_client
        cls.certificates_client = cls.os.certificates_client
        cls.migrations_client = cls.os.migrations_client
        cls.security_group_default_rules_client = (
            cls.os.security_group_default_rules_client)
        cls.versions_client = cls.os.compute_versions_client

	if CONF.volume_feature_enabled.api_v1:
            cls.volumes_client = cls.os.volumes_client
        else:
            cls.volumes_client = cls.os.volumes_v2_client
    @classmethod
    def register_custom_config_opts(cls):
        conf = cfg.CONF
        volume_opts = [
                   cfg.StrOpt('volume_type_nfs', default='123233'),
                   cfg.StrOpt('volume_type_ceph', default='31312323'),
                ]
        conf.register_opt(volume_opts, group='volume')

    @classmethod
    def resource_setup(cls):
        super(BaseWorkloadmgrTest, cls).resource_setup()

    @classmethod
    def resource_cleanup(cls):
        super(BaseWorkloadmgrTest, cls).resource_cleanup()

    '''
    Method returns the current status of a given workload
    '''
    def getWorkloadStatus(self, workload_id):
        resp, body = self.wlm_client.client.get("/workloads/"+workload_id)
        workload_status = body['workload']['status']
        LOG.debug("#### workloadid: %s , operation:show_workload" % workload_id)
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return workload_status

    '''
    Method returns the current status of a given snapshot
    '''
    def getSnapshotStatus(self, workload_id, snapshot_id):
        resp, body = self.wlm_client.client.get("/workloads/"+workload_id+"/snapshots/"+snapshot_id)
        snapshot_status = body['snapshot']['status']
        LOG.debug("#### workloadid: %s ,snapshot_id: %s , operation:show_snapshot" % (workload_id, snapshot_id))
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return snapshot_status

    '''
    Method returns the current status of a given restore
    '''
    def getRestoreStatus(self, workload_id, snapshot_id, restore_id):
        resp, body = self.wlm_client.client.get("/workloads/"+workload_id+"/snapshots/"+snapshot_id+"/restores/"+restore_id)
        restore_status = body['restore']['status']
        LOG.debug("#### workloadid: %s ,snapshot_id: %s, restore_id: %s, operation: show_restore" % (workload_id, snapshot_id, restore_id))
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return restore_status

    '''
    Method returns the schedule status of a given workload
    '''
    def getSchedulerStatus(self, workload_id):
        resp, body = self.wlm_client.client.get("/workloads/"+workload_id)
        schedule_status = body['workload']['jobschedule']['enabled']
        LOG.debug("#### workloadid: %s , operation:show_workload" % workload_id)
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return schedule_status

    '''
    Method returns the Retention Policy Type status of a given workload
    '''
    def getRetentionPolicyTypeStatus(self, workload_id):
        resp, body = self.wlm_client.client.get("/workloads/"+workload_id)
        retention_policy_type = body['workload']['jobschedule']['retention_policy_type']
        LOG.debug("#### workloadid: %s , operation:show_workload" % workload_id)
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return retention_policy_type

    '''
    Method returns the Retention Policy Value of a given workload
    '''
    def getRetentionPolicyValueStatus(self, workload_id):
        resp, body = self.wlm_client.client.get("/workloads/"+workload_id)
        retention_policy_value = body['workload']['jobschedule']['retention_policy_value']
        LOG.debug("#### workloadid: %s , operation:show_workload" % workload_id)
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return retention_policy_value

    '''
    Method returns the Full Backup Interval status of a given workload
    '''
    def getFullBackupIntervalStatus(self, workload_id):
        resp, body = self.wlm_client.client.get("/workloads/"+workload_id)
        Full_Backup_Interval_Value = body['workload']['jobschedule']['fullbackup_interval']
        LOG.debug("#### workloadid: %s , operation:show_workload" % workload_id)
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return Full_Backup_Interval_Value

    '''
    Method raises exception if snapshot is not successful
    '''
    def assertSnapshotSuccessful(self, workload_id, snapshot_id):
        snapshot_status = self.getSnapshotStatus(workload_id, snapshot_id)
        self.assertEqual(snapshot_status, "available")

    '''
    Method raises exception if restore is not successful
    '''
    def assertRestoreSuccessful(self, workload_id, snapshot_id, restore_id):
        restore_status = self.getRestoreStatus(workload_id, snapshot_id, restore_id)
        self.assertEqual(restore_status, "available")

    '''
    Method raises exception if scheduler is not enabled for a given workload
    '''
    def assertSchedulerEnabled(self, workload_id):
        scheduler_status = self.getSchedulerStatus(workload_id)
        self.assertEqual(scheduler_status, "true")

    '''
    Method returns the Instance ID of a new VM instance created
    '''
    def create_vm(self, vm_cleanup=True, vm_name="Tempest_Test_Vm", security_group_id = "default", flavor_id =CONF.compute.flavor_ref, key_pair = "", networkid=[{'uuid':CONF.network.internal_network_id}]):
        if(tvaultconf.vms_from_file and self.is_vm_available()):
            server_id=self.read_vm_id()
        else:
            if key_pair:
                server=self.servers_client.create_server(name=vm_name,security_groups = [{"name":security_group_id}], imageRef=CONF.compute.image_ref, flavorRef=flavor_id, networks=networkid, key_name=tvaultconf.key_pair_name)
            else:
                server=self.servers_client.create_server(name=vm_name,security_groups = [{"name":security_group_id}], imageRef=CONF.compute.image_ref, flavorRef=flavor_id, networks=networkid)
            server_id= server['server']['id']
            waiters.wait_for_server_status(self.servers_client, server_id, status='ACTIVE')
        if(tvaultconf.cleanup == True and vm_cleanup == True):
	    self.addCleanup(self.delete_vm, server_id)
        return server_id

    '''
    Method returns the Instance IDs of the new VM instances created
    '''
    def create_vms(self, totalVms):
        instances = []
        for vm in range(0,totalVms):
            if(tvaultconf.vms_from_file):
                flag=0
                flag=self.is_vm_available()
                if(flag != 0):
                    server_id=self.read_vm_id()
                else:
                    server=self.servers_client.create_server(name="tempest-test-vm", imageRef=CONF.compute.image_ref, flavorRef=CONF.compute.flavor_ref,key_name=tvaultconf.key_pair_name)
                    server_id=server['server']['id']
                    waiters.wait_for_server_status(self.servers_client, server['server']['id'], status='ACTIVE')
            else:
                server=self.servers_client.create_server(name="tempest-test-vm", imageRef=CONF.compute.image_ref, flavorRef=CONF.compute.flavor_ref,key_name=tvaultconf.key_pair_name)
                #instances.append(server['server']['id'])
                server_id=server['server']['id']
                waiters.wait_for_server_status(self.servers_client, server['server']['id'], status='ACTIVE')
            instances.append(server_id)
        if(tvaultconf.cleanup):
            self.addCleanup(self.delete_vms, instances)
        return instances

    '''
    Method deletes the given VM instance
    '''
    def delete_vm(self, server_id):
        try:
	    self.delete_port(server_id)
            body = self.servers_client.show_server(server_id)['server']
            self.servers_client.delete_server(server_id)
            waiters.wait_for_server_termination(self.servers_client, server_id)
        except lib_exc.NotFound:
            return

    '''
    Method deletes the given VM instances list
    '''
    def delete_vms(self, instances):
        totalVms = len(instances)
        for vm in range(0,totalVms):
            try:
		self.delete_vm(instances[vm])
            except Exception as e:
                pass
        LOG.debug('DeletedVms: %s' % instances)

    '''
    Method creates a new volume and returns Volume ID
    '''
    def create_volume(self, size, volume_type_id, volume_cleanup=True):
        self.expected_resp = 200
	LOG.debug("Expected Response Code: " + str(self.expected_resp))
        if(tvaultconf.volumes_from_file):
            flag=0
            flag=self.is_volume_available()
            if(flag != 0):
                volume_id=self.read_volume_id()
            else:
                volume = self.volumes_client.create_volume(size=size, expected_resp=self.expected_resp, volume_type=volume_type_id)
                volume_id= volume['volume']['id']
                waiters.wait_for_volume_status(self.volumes_client,
                                       volume_id, 'available')
        else:
            volume = self.volumes_client.create_volume(size=size, expected_resp=self.expected_resp, volume_type=volume_type_id)
            volume_id= volume['volume']['id']
            waiters.wait_for_volume_status(self.volumes_client,
                                       volume_id, 'available')
        if(tvaultconf.cleanup == True and volume_cleanup == True):
            self.addCleanup(self.delete_volume, volume_id)
        return volume_id

    '''
    Method deletes a given volume
    '''
    def delete_volume(self, volume_id):
        try:
	    volume_snapshots = self.get_volume_snapshots(volume_id)
	    LOG.debug("Volumes snapshots for: " + str(volume_id) + ": " + str(volume_snapshots))
	    self.delete_volume_snapshots(volume_snapshots)
	    LOG.debug("Deletion of volume: " + str(volume_id) + "started")
            self.volumes_extensions_client.delete_volume(volume_id)
        except Exception as e:
            return

    '''
    Method deletes a given volume snapshot
    '''
    def delete_volume_snapshot(self, volume_snapshot_id):
        try:
            self.snapshots_extensions_client.delete_snapshot(volume_snapshot_id)
            LOG.debug('Snapshot delete operation completed %s' % volume_snapshot_id)
            time.sleep(60)
        except Exception as e:
            return

    '''
    Method deletes a list of volume snapshots
    '''
    def delete_volume_snapshots(self, volume_snapshots):
        for snapshot in range(0, len(volume_snapshots)):
            try:
                self.delete_volume_snapshot(volume_snapshots[snapshot])
                LOG.debug('Snapshot delete operation completed %s' % volume_snapshots[snapshot])
            except Exception as e:
                LOG.error("Exception: " + str(e))

    '''
    Method to return list of available volume snapshots
    '''
    def get_available_volume_snapshots(self):
        volume_snapshots = []
        resp = self.snapshots_extensions_client.list_snapshots(detail=True)
        for id in range(0,len(resp['snapshots'])):
            volume_snapshots.append(resp['snapshots'][id]['id'])
        LOG.debug("Volume snapshots: " + str(volume_snapshots))
        return volume_snapshots

    '''
    Method to return list of available volume snapshots for given volume
    '''
    def get_volume_snapshots(self, volume_id):
        volume_snapshots = []
        resp = self.snapshots_extensions_client.list_snapshots(detail=True)
        for id in range(0,len(resp['snapshots'])):
            volume_snapshot_id = resp['snapshots'][id]['volumeId']
            if ( volume_id == volume_snapshot_id ):
                volume_snapshots.append(resp['snapshots'][id]['id'])
        LOG.debug("Volume snapshots: " + str(volume_snapshots))
        return volume_snapshots

    '''
    Method returns the list of attached volumes to a given VM instance
    '''
    def get_attached_volumes(self, server_id):
        server = self.servers_client.show_server(server_id)['server']
        volumes=server['os-extended-volumes:volumes_attached']
        volume_list = []
        for volume in volumes:
            volume_list.append(volume['id']);
        LOG.debug("Attached volumes: "+ str(volume_list))
        return volume_list

    '''
    Method deletes the given volumes list
    '''
    def delete_volumes(self, volumes):
        for volume in volumes:
            try:
                self.delete_volume(volume)
                LOG.debug('Volume delete operation completed %s' % volume)
            except Exception as e:
		LOG.debug("Exception" + str(e))
                pass

    '''
    Method attaches given volume to given VM instance
    '''
    def attach_volume(self, volume_id, server_id, device="/dev/vdb", attach_cleanup=False):
        #device = "/dev/"+''.join(choice(ascii_lowercase) for i in range(10))
        #device = "/dev/vdb"
        #self.volumes_client.attach_volume(volume_id,
        #                          server_id,
        #                          device)
        if( not tvaultconf.workloads_from_file):
            if(tvaultconf.volumes_from_file):
                try:
                    LOG.debug("attach_volume: volumeId: %s, serverId: %s"  % (volume_id, server_id))
                    self.servers_client.attach_volume(server_id, volumeId=volume_id, device=device)
                    self.volumes_client.wait_for_volume_status(volume_id, 'in-use')
                except Exception as e:
                    pass
            else:
                LOG.debug("attach_volume: volumeId: %s, serverId: %s"  % (volume_id, server_id))
                self.servers_client.attach_volume(server_id, volumeId=volume_id, device=device)
                self.volumes_client.wait_for_volume_status(volume_id, 'in-use')
        if(tvaultconf.cleanup == True and attach_cleanup == True):
            self.addCleanup(self.detach_volume, server_id, volume_id)

    '''
    Method to detach given volume from given VM instance
    '''
    def detach_volume(self, server_id, volume_id):
        #cls.volumes_client.detach_volume(volume_id)
        #waiters.wait_for_volume_status(cls.volumes_client,
        #                               volume_id, 'available')
        try:
            body = self.volumes_client.show_volume(volume_id)['volume']
            self.servers_client.detach_volume(server_id, volume_id)
            self.volumes_client.wait_for_volume_status(volume_id, 'available')
        except lib_exc.NotFound:
            return

    '''
    Method to detach given list of volumes
    '''
    def detach_volumes(self, volumes):
        total_volumes = len(volumes)
        for volume in range(0, total_volumes):
            self.volumes_client.detach_volume(volumes[volume])
            LOG.debug('Volume detach operation completed %s' % volume)
            waiters.wait_for_volume_status(self.volumes_client,
                                       volumes[volume], 'available')

    '''
    Method creates a workload and returns Workload id
    '''
    def workload_create(self, instances, workload_type ,jobschedule={}, workload_name="", workload_cleanup=True, description='test'):
        if(tvaultconf.workloads_from_file):
            flag=0
            flag=self.is_workload_available()
            if(flag != 0):
                workload_id=self.read_workload_id()
            else:
                in_list = []
                ts=str(datetime.now())
                workload_name = "tempest"+ ts
                for id in instances:
                    in_list.append({'instance-id':id})
                payload={'workload': {'name': workload_name,
                              'workload_type_id': workload_type,
                              'source_platform': 'openstack',
                              'instances': in_list,
                              'jobschedule': jobschedule,
                              'metadata': {},
                              'description': description}}
                resp, body = self.wlm_client.client.post("/workloads", json=payload)
                workload_id = body['workload']['id']
                LOG.debug("#### workloadid: %s , operation:workload_create" % workload_id)
                LOG.debug("Response:"+ str(resp.content))
                if(resp.status_code != 202):
                    resp.raise_for_status()
        else:
            in_list = []
            if(workload_name == ""):
                ts=str(datetime.now())
                workload_name = "tempest"+ ts
            for id in instances:
                in_list.append({'instance-id':id})
            payload={'workload': {'name': workload_name,
                              'workload_type_id': workload_type,
                              'source_platform': 'openstack',
                              'instances': in_list,
                              'jobschedule': jobschedule,
                              'metadata': {},
                              'description': description}}
            resp, body = self.wlm_client.client.post("/workloads", json=payload)
            workload_id = body['workload']['id']
            LOG.debug("#### workloadid: %s , operation:workload_create" % workload_id)
            time.sleep(30)
            while (self.getWorkloadStatus(workload_id) != "available" and self.getWorkloadStatus(workload_id) != "error"):
                LOG.debug('workload status is: %s , sleeping for 30 sec' % self.getWorkloadStatus(workload_id))
                time.sleep(30)

            LOG.debug("Response:"+ str(resp.content))
            if(resp.status_code != 202):
                resp.raise_for_status()
        LOG.debug('WorkloadCreated: %s' % workload_id)
        if(tvaultconf.cleanup == True and workload_cleanup == True):
            self.addCleanup(self.workload_delete, workload_id)
        return workload_id

    '''
    Method deletes a given workload
    '''
    def workload_delete(self, workload_id):
        try:
            resp, body = self.wlm_client.client.delete("/workloads/"+workload_id)
            LOG.debug("#### workloadid: %s , operation: workload_delete" % workload_id)
            LOG.debug("Response:"+ str(resp.content))
	    LOG.debug('WorkloadDeleted: %s' % workload_id)
	    return True
        except Exception as e:
            return False

    '''
    Method creates oneclick snapshot for a given workload and returns snapshot id
    '''
    def workload_snapshot(self, workload_id, is_full, snapshot_name="", snapshot_cleanup=True):
        if (snapshot_name == ""):
            snapshot_name = 'Tempest-test-snapshot'
        LOG.debug("Snapshot Name: " + str(snapshot_name))
        payload={'snapshot': { 'name': snapshot_name,
                               'description': 'Test',
                               'full': 'True'}}
        LOG.debug("Snapshot Payload: " + str(payload))
        self.wait_for_workload_tobe_available(workload_id)
        if(is_full):
            resp, body = self.wlm_client.client.post("/workloads/"+workload_id+"?full=1",json=payload)
        else:
            resp, body = self.wlm_client.client.post("/workloads/"+workload_id,json=payload)
        snapshot_id = body['snapshot']['id']
        LOG.debug("#### workload_id: %s ,snapshot_id: %s , operation: workload_snapshot" % (workload_id, snapshot_id))
        LOG.debug("Snapshot Response:"+ str(resp.content))
        self.wait_for_workload_tobe_available(workload_id)
        if(tvaultconf.cleanup == True and snapshot_cleanup == True):
            self.addCleanup(self.snapshot_delete,workload_id, snapshot_id)
        return snapshot_id

    '''
    Method resets the given workload
    '''
    def workload_reset(self, workload_id):
        self.wait_for_workload_tobe_available(workload_id)
        resp, body = self.wlm_client.client.post("/workloads/"+workload_id+"/reset")
        LOG.debug("#### workloadid: %s, operation: workload-reset " % workload_id)
        LOG.debug("Response:"+ str(resp.content))
        LOG.debug("Response code:"+ str(resp.status_code))
        if (resp.status_code != 202):
            resp.raise_for_status()

    '''
    Method to wait until the workload is available
    '''
    def wait_for_workload_tobe_available(self, workload_id):
        status = "available"
        start_time = int(time.time())
        LOG.debug('Checking workload status')
        while ( status != self.getWorkloadStatus(workload_id)):
            if ( self.getWorkloadStatus(workload_id) == 'error'):
                LOG.debug('workload status is: %s , workload create failed' % self.getWorkloadStatus(workload_id))
                #raise Exception("Workload creation failed")
		return False
            LOG.debug('workload status is: %s , sleeping for 30 sec' % self.getWorkloadStatus(workload_id))
            time.sleep(30)
        LOG.debug('workload status of workload %s: %s' % (workload_id, self.getWorkloadStatus(workload_id)))
	return True

    '''
    Method to check if snapshot is successful
    '''
    def is_snapshot_successful(self, workload_id, snapshot_id):
        is_successful= "False"
        if(self.getSnapshotStatus(workload_id, snapshot_id) == 'available'):
            LOG.debug('snapshot successful: %s' % snapshot_id)
            is_successful = "True"
        return is_successful

    '''
    Method deletes a given snapshot
    '''
    def snapshot_delete(self, workload_id, snapshot_id):
        resp, body = self.wlm_client.client.delete("/snapshots/"+str(snapshot_id))
        LOG.debug("#### workloadid: %s ,snapshot_id: %s  , Operation: snapshot_delete" % (workload_id, snapshot_id))
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 202):
            resp.raise_for_status()
        self.wait_for_workload_tobe_available(workload_id)
        LOG.debug('SnapshotDeleted: %s' % workload_id)
	return True

    '''
    Method creates one click restore for a given snapshot and returns the restore id
    '''
    def snapshot_restore(self, workload_id, snapshot_id, restore_name="", restore_cleanup=True):
        LOG.debug("At the start of snapshot_restore method")
        if(restore_name == ""):
            restore_name = tvaultconf.snapshot_restore_name
        payload={"restore": {"options": {"description": "Tempest test restore",
                                           "vmware": {},
                                           "openstack": {"instances": [], "zone": ""},
					   "restore_type": "oneclick",
                                           "type": "openstack",
                                           "restore_options": {},
                                           "name": restore_name},
                "name": restore_name,
                "description": "Tempest test restore"}}
        LOG.debug("In snapshot_restore method, before calling waitforsnapshot method")
        self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
        LOG.debug("After returning from wait for snapshot")
        resp, body = self.wlm_client.client.post("/workloads/"+workload_id+"/snapshots/"+snapshot_id+"/restores",json=payload)
        restore_id = body['restore']['id']
        LOG.debug("#### workloadid: %s ,snapshot_id: %s , restore_id: %s , operation: snapshot_restore" % (workload_id, snapshot_id, restore_id))
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 202):
            resp.raise_for_status()
        LOG.debug('Restore of snapshot %s scheduled succesffuly' % snapshot_id)
        #self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
        if(tvaultconf.cleanup == True and restore_cleanup == True):
            self.restored_vms = self.get_restored_vm_list(restore_id)
	    self.restored_volumes = self.get_restored_volume_list(restore_id)
            self.addCleanup(self.restore_delete, workload_id, snapshot_id, restore_id)
            self.addCleanup(self.delete_restored_vms, self.restored_vms, self.restored_volumes)
        return restore_id

    '''
    Method creates selective restore for a given snapshot and returns the restore id
    '''
    def snapshot_selective_restore(self, workload_id, snapshot_id, restore_name="", restore_desc="", instance_details=[], network_details=[], restore_cleanup=True, sec_group_cleanup = False):
        LOG.debug("At the start of snapshot_selective_restore method")
        if(restore_name == ""):
            restore_name = "Tempest_test_restore"
        if(restore_desc == ""):
            restore_desc = "Tempest_test_restore_description"
        if len(instance_details) > 0:
            payload={
                "restore": {
                    "options": {
                        'name': restore_name,
                        'description': restore_desc,
                        'type': 'openstack',
                        'restore_type': 'selective',
                        'openstack': {
                            'instances': instance_details,
                            'networks_mapping': { 'networks': network_details }
                                     }
                                }
                           }
                     }
            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            resp, body = self.wlm_client.client.post("/workloads/"+workload_id+"/snapshots/"+snapshot_id+"/restores",json=payload)
            restore_id = body['restore']['id']
            LOG.debug("#### workloadid: %s ,snapshot_id: %s , restore_id: %s , operation: snapshot_restore" % (workload_id, snapshot_id, restore_id))
            LOG.debug("Response:"+ str(resp.content))
            if(resp.status_code != 202):
                resp.raise_for_status()
            LOG.debug('Restore of snapshot %s scheduled succesffuly' % snapshot_id)
            if(tvaultconf.cleanup == True and restore_cleanup == True):
		self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
                self.restored_vms = self.get_restored_vm_list(restore_id)
                self.restored_volumes = self.get_restored_volume_list(restore_id)
		self.addCleanup(self.restore_delete, workload_id, snapshot_id, restore_id)
		if sec_group_cleanup == True:
		    self.restored_security_group_id = self.get_security_group_id_by_name("snap_of_" + tvaultconf.security_group_name)
		    self.addCleanup(self.delete_security_group, self.restored_security_group_id)
                self.addCleanup(self.delete_restored_vms, self.restored_vms, self.restored_volumes)
        else:
            restore_id = 0
        return restore_id

    '''
    Method returns the list of restored VMs
    '''
    def get_restored_vm_list(self, restore_id):
        resp, body = self.wlm_client.client.get("/restores/"+str(restore_id))
        LOG.debug("Body: " + str(body))
        LOG.debug("Response: " + str(resp))
        instances= body['restore']['instances']
        restore_vms = []
        for instance in instances:
            LOG.debug("instance:"+ instance['id'])
            restore_vms.append(instance['id'])
        LOG.debug("Restored vms list:"+ str(restore_vms))
        return restore_vms

    '''
    Method returns the list of restored volumes
    '''
    def get_restored_volume_list(self, restore_id):
        resp, body = self.wlm_client.client.get("/restores/"+restore_id)
        LOG.debug("Body: " + str(body))
        LOG.debug("Response: " + str(resp))
        instances= body['restore']['instances']
        restored_volumes = []
        for instance in instances:
            LOG.debug("instance:"+ instance['id'])
            if len(self.get_attached_volumes(instance['id'])) > 0:
		for volume in self.get_attached_volumes(instance['id']):
		    restored_volumes.append(volume)
        LOG.debug("restored volume list:"+ str(restored_volumes))
        return restored_volumes

    '''
    Method deletes the given restored VMs and volumes
    '''
    def delete_restored_vms(self, restored_vms, restored_volumes):
	LOG.debug("Deletion of retored vms started.")
        self.delete_vms(restored_vms)
	LOG.debug("Deletion of restored volumes started.")
        self.delete_volumes(restored_volumes)

    '''
    Method to wait until the snapshot is available
    '''
    def wait_for_snapshot_tobe_available(self, workload_id, snapshot_id):
        status = "available"
        LOG.debug('Checking snapshot status')
        while (status != self.getSnapshotStatus(workload_id, snapshot_id)):
            if(self.getSnapshotStatus(workload_id, snapshot_id) == 'error'):
                LOG.debug('Snapshot status is: %s' % self.getSnapshotStatus(workload_id, snapshot_id))
                raise Exception("Snapshot creation failed")
            LOG.debug('Snapshot status is: %s' % self.getSnapshotStatus(workload_id, snapshot_id))
            time.sleep(10)
        LOG.debug('Final Status of snapshot: %s' % (self.getSnapshotStatus(workload_id, snapshot_id)))
        return status

    '''
    Method to check if restore is successful
    '''
    def is_restore_successful(self, workload_id, snapshot_id, restore_id):
        is_successful= "False"
        if(self.getRestoreStatus(workload_id, snapshot_id, restore_id) == 'available'):
            is_successful = "True"
        return is_successful

    '''
    Method returns if scheduler is running for a given workload
    '''
    def is_schedule_running(self,workload_id):
        is_running = False
        snapshot_list = self.getSnapshotList(workload_id)
        for i in range (0,(len(snapshot_list))):
            FMT = "%Y-%m-%dT%H:%M:%S.000000"
            snapshot_info = []
            snapshot_info = self.getSnapshotInfo(snapshot_list[i])
            SnapshotCreateTime = snapshot_info[0]
            LOG.debug('snapshot create time is: %s' % SnapshotCreateTime)
            SnapshotNameInfo = snapshot_info[1]
            if (i==0):
                if(SnapshotNameInfo == 'jobscheduler'):
                    is_running = True
                    LOG.debug('snapshot is running: %s' % snapshot_list[i])
                    self.wait_for_workload_tobe_available(workload_id)
                else:
                    LOG.debug('snapshot is not running: %s' % snapshot_list[i])
                    is_running = False
            else:
                previous_snapshot_info = self.getSnapshotInfo(snapshot_list[i-1])
                SnapshotCreateTime1 = previous_snapshot_info[0]
                tdelta = datetime.strptime(SnapshotCreateTime, FMT) - datetime.strptime(SnapshotCreateTime1, FMT)
                LOG.debug('Time Interval Between Two snapshot is: %s' % str(tdelta))
                if(SnapshotNameInfo == 'jobscheduler' and (str(tdelta)=="1:00:00")):
                    is_running = True
                    LOG.debug('snapshot is running: %s' %str(tdelta))
                    self.wait_for_workload_tobe_available(workload_id)
                else:
                    LOG.debug('snapshot is not running: %s' % snapshot_list[i])
                    is_running = False
        return is_running

    '''
    Method to delete a given restore
    '''
    def restore_delete(self, workload_id, snapshot_id, restore_id):
        self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
        resp, body = self.wlm_client.client.delete("/workloads/"+workload_id+"/snapshots/"+snapshot_id+"/restores/"+restore_id)
        LOG.debug("#### workloadid: %s ,snapshot_id: %s  , Operation: snapshot_delete" % (workload_id, snapshot_id))
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 202):
            resp.raise_for_status()
        self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
        LOG.debug('SnapshotDeleted: %s' % workload_id)

    '''
    Method to check if VM details are available in file
    '''
    def is_vm_available(self):
        dir=os.path.dirname(os.path.abspath(__file__))
        filename=dir+"/vms_file"
        LOG.debug("vms_file_path:%s" % filename)
        with open(filename) as f:
            content = f.read().splitlines()
            if not content:
                return False
            else:
                LOG.debug ("vm_from_file: %s" % content[0])
                return True

    '''
    Method to return the VM id from file
    '''
    def read_vm_id(self):
        dir=os.path.dirname(os.path.abspath(__file__))
        filename=dir+"/vms_file"
        LOG.debug("vms_file_path:%s" % filename)
        with open(filename, "r+") as f:
            vms = f.read().splitlines()
            vm_id=vms[0]
            f.seek(0)
            for vm in vms:
                if vm !=vm_id:
                   f.write(vm)
            f.truncate()
            return vm_id

    '''
    Method to check if volume details are available in file
    '''
    def is_volume_available(self):
        dir=os.path.dirname(os.path.abspath(__file__))
        filename=dir+"/volumes_file"
        LOG.debug("volumes_file_path:%s" % filename)
        with open(filename) as f:
            content = f.read().splitlines()
            if not content:
                return False
            else:
                LOG.debug ("volume_from_file: %s" % content[0])
                return True

    '''
    Method to return the volume id from file
    '''
    def read_volume_id(self):
        dir=os.path.dirname(os.path.abspath(__file__))
        filename=dir+"/volumes_file"
        LOG.debug("volumes_file_path:%s" % filename)
        with open(filename, "r+") as f:
            volumes = f.read().splitlines()
            volume_id=volumes[0]
            f.seek(0)
            for volume in volumes:
                if volume !=volume_id:
                    f.write(volume)
            f.truncate()
            return volume_id

    '''
    Method to check if workload details are available in file
    '''
    def is_workload_available(self):
        dir=os.path.dirname(os.path.abspath(__file__))
        filename=dir+"/workloads_file"
        LOG.debug("workloads_file_path:%s" % filename)
        with open(filename) as f:
            content = f.read().splitlines()
            if not content:
                return False
            else:
                LOG.debug ("workload_from_file: %s" % content[0])
                return True

    '''
    Method to return the workload id from file
    '''
    def read_workload_id(self):
        dir=os.path.dirname(os.path.abspath(__file__))
        filename=dir+"/workloads_file"
        LOG.debug("workloads_file_path:%s" % filename)
        with open(filename, "r+") as f:
            workloads = f.read().splitlines()
            workload_id=workloads[0]
            f.seek(0)
            for workload in workloads:
                if workload !=workload_id:
                    f.write(workload)
            f.truncate()
            return workload_id

    '''
    Method to write scheduler details in file
    '''
    def verifyScheduleTest(self, workload_id):
        tvaultconf.count = tvaultconf.count + 1
        LOG.debug("tvaultconf.count value is:%s" % tvaultconf.count)
        f = open(tvaultconf.schedule_report_file, "a")
        if (self.is_schedule_running(workload_id)):
            date = time.strftime("%c")
            f.write('Snapshot is running : ' +str(date)+ '\n')
        else :
            date=time.strftime("%c")
            f.write('Snapshot Not running : ' +str(date)+ '\n')
            tvaultconf.sched.remove_job('my_job_id')
            tvaultconf.sched.shutdown(wait=False)
        if (tvaultconf.count == tvaultconf.No_of_Backup):
            tvaultconf.sched.remove_job('my_job_id')
            tvaultconf.sched.shutdown(wait=False)

    '''
    Method to fetch the list of network ports
    '''
    def get_port_list(self):
        port_list = self.network_client.list_ports()
        LOG.debug("Port List: " + str(port_list))
        return port_list

    '''
    Method to delete list of ports
    '''
    def delete_ports(self, port_list):
        for i in range(0,len(port_list)):
            port_delete = self.network_client.delete_port(port_list[i])
            LOG.debug("Port %s status %s" % (port_list[i], port_delete))

    '''
    Method returns the snapshot list information
    '''
    def getSnapshotList(self, workload_id='none'):
        resp, body = self.wlm_client.client.get("/snapshots?workload_id="+workload_id)
        snapshot_list = []
        for i in range(0,len(body['snapshots'])):
            snapshot_list.append(body['snapshots'][i]['id'])
            LOG.debug('snapshot id is: %s' % snapshot_list[i])
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
           resp.raise_for_status()
        return snapshot_list


    '''
    Method returns the snapshot information . It return array with create time,name and type information for given snapshot
    '''
    def getSnapshotInfo(self, snapshot_id='none'):
        resp, body = self.wlm_client.client.get("/snapshots/"+snapshot_id)
        snapshot_info = []
        snapshot_create_time_info = body['snapshot']['created_at']
        snapshot_info.append(snapshot_create_time_info)
        LOG.debug('snapshot create time is: %s' % snapshot_info[0])
        snapshot_name_info = body['snapshot']['name']
        snapshot_info.append(snapshot_name_info)
        LOG.debug('snapshot name is: %s' % snapshot_info[1])
        snapshot_type_info = body['snapshot']['snapshot_type']
        snapshot_info.append(snapshot_type_info)
        LOG.debug('snapshot type is : %s' % snapshot_info[2])
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
           resp.raise_for_status()
        return snapshot_info

    '''
    Method to connect to remote linux machine
    '''
    def SshRemoteMachineConnection(self, ipAddress, userName, password):
        ssh=paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.load_system_host_keys()
        ssh.connect(hostname=ipAddress, username=userName ,password=password)
        return ssh

    '''
    Method to list all floating ips
    '''
    def get_floating_ips(self):
        floating_ips_list = []
        get_ips_response = self.floating_ips_client.list_floating_ips()
        LOG.debug("get floating ips response: " + str(get_ips_response))
        floating_ips = get_ips_response['floating_ips']
        for ip in floating_ips:
            LOG.debug("instanceid: " + str(ip['instance_id']))
            if str(ip['instance_id']) == "None" or str(ip['instance_id']) == "":
                floating_ips_list.append(ip['ip'])
        LOG.debug('floating_ips' + str(floating_ips_list))
        return floating_ips_list

    '''
    Method to associate floating ip to a server
    '''
    def set_floating_ip(self, floating_ip, server_id, floatingip_cleanup=False):
        set_response = self.floating_ips_client.associate_floating_ip_to_server(floating_ip, server_id)
        #self.SshRemoteMachineConnectionWithRSAKey(floating_ip)
        if(tvaultconf.cleanup == True and floatingip_cleanup == True):
            self.addCleanup(self.disassociate_floating_ip_from_server, floating_ip, server_id)
        return set_response

    '''
    Method to create SSH connection using RSA Private key
    '''
    def SshRemoteMachineConnectionWithRSAKey(self, ipAddress):
        username = tvaultconf.instance_username
        key_file = str(tvaultconf.key_pair_name) + ".pem"
        ssh=paramiko.SSHClient()
        private_key = paramiko.RSAKey.from_private_key_file(key_file)
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.load_system_host_keys()
        flag = True
        for i in range(0, 30, 1):
            LOG.debug("Trying to connect to " + str(ipAddress))
            try:
                ssh.connect(hostname=ipAddress, username=username ,pkey=private_key, timeout = 20)
            except Exception as e:
                time.sleep(15)
                if i == 29:
                    raise
                LOG.debug("Got into Exception.." + str(e))
            else:
                break
        return ssh

    '''
    layout creation and formatting the disks
    '''
    def execute_command_disk_create(self, ssh, ipAddress, volumes, mount_points):
        stdin, stdout, stderr = ssh.exec_command("sudo sfdisk -d /dev/vda > my.layout")
        stdin, stdout, stderr = ssh.exec_command("sudo cat my.layout")
        LOG.debug("disk create my.layout output" + str(stdout.read()))
	for volume in volumes:
            stdin, stdout, stderr = ssh.exec_command("sudo sfdisk " + volume + " < my.layout")
            stdin, stdout, stderr = ssh.exec_command("sudo fdisk -l | grep /dev/vd")
            LOG.debug("fdisk output after partitioning " + str(stdout.read()))
            # vdb1
	    time.sleep(5)
            buildCommand = "sudo mkfs -t ext3 " + volume + "1"
            sleeptime = 2
            outdata, errdata = '', ''
            ssh_transp = ssh.get_transport()
            chan = ssh_transp.open_session()
            # chan.settimeout(3 * 60 * 60)
            chan.setblocking(0)
            chan.exec_command(buildCommand)
            LOG.debug("sudo mkfs -t ext3 " + volume + "1 executed")
            while True:  # monitoring process
                # Reading from output streams
                while chan.recv_ready():
                    outdata += chan.recv(1000)
                while chan.recv_stderr_ready():
                    errdata += chan.recv_stderr(1000)
                if chan.exit_status_ready():  # If completed
                    break
                time.sleep(sleeptime)
                LOG.debug("sudo mkfs -t ext3  " + volume + "1 output waiting..")
            retcode = chan.recv_exit_status()
	
	for mount_point in mount_points:
            stdin, stdout, stderr = ssh.exec_command("sudo mkdir " + "\\" + mount_point)

    '''
    disks mounting
    '''
    def execute_command_disk_mount(self, ssh, ipAddress, volumes,  mount_points):
        LOG.debug("Execute command disk mount connecting to " + str(ipAddress))
        # stdin, stdout, stderr = ssh_con.exec_command("sudo mount /dev/vdb1 mount_data_b")
	for i in range(len(volumes)):
            buildCommand = "sudo mount " + volumes[i] + "1 " + mount_points[i]
            sleeptime = 1
            outdata, errdata = '', ''
            ssh_transp = ssh.get_transport()
            chan = ssh_transp.open_session()
            chan.setblocking(0)
            chan.exec_command(buildCommand)
            while True:  # monitoring process
                # Reading from output streams
                while chan.recv_ready():
                    outdata += chan.recv(1000)
                while chan.recv_stderr_ready():
                    errdata += chan.recv_stderr(1000)
                if chan.exit_status_ready():  # If completed
                    break
                time.sleep(sleeptime)
                LOG.debug("sudo mount output waiting..")
            retcode = chan.recv_exit_status()
	    
	    # check mounts in df -h output
	    stdin, stdout, stderr = ssh.exec_command("sudo df -h")
	    output = stdout.read()
            LOG.debug("sudo df -h after mounting " + volumes[i] + "1 :" + str(output))
	    if str(volumes[i]+"1") in str(output):
		LOG.debug("mounting completed for " + str(ipAddress))
	    else:	    
		raise Exception("Mount point failed for " + str(ipAddress))

    '''
    add custom sied files on linux
    '''
    def addCustomSizedfilesOnLinux(self, ssh, dirPath,fileCount):
        try:
            LOG.debug("build command data population : " + str(dirPath))
            for count in range(fileCount):
                buildCommand = "sudo openssl rand -out " + str(dirPath) + "/" + "File" +"_"+str(count+1) + ".txt -base64 $(( 2**25 * 3/4 ))"
                # stdin, stdout, stderr = ssh.exec_command(buildCommand)
                outdata, errdata = '', ''
                ssh_transp = ssh.get_transport()
                chan = ssh_transp.open_session()
                # chan.settimeout(3 * 60 * 60)
                chan.setblocking(0)
                chan.exec_command(buildCommand)
                time.sleep(20)
                while True:  # monitoring process
                    # Reading from output streams
                    while chan.recv_ready():
                        outdata += chan.recv(1000)
                    while chan.recv_stderr_ready():
                        errdata += chan.recv_stderr(1000)
                    if chan.exit_status_ready():  # If completed
                        break
                    time.sleep(2)
                    # LOG.debug(str(buildCommand)+ " waiting..")
                retcode = chan.recv_exit_status()
                # stdin, stdout, stderr = ssh.exec_command("sudo ls -l " + str(dirPath))
                # LOG.debug("file change output:" + str(stdout.read()))
        except Exception as e:
            LOG.debug("Exception: " + str(e))

    '''
    calculate md5 checksum
    '''
    def calculatemmd5checksum(self, ssh, dirPath):
        try:
            local_md5sum = ""
            buildCommand = "sudo find " + str(dirPath) + """/ -type f -exec md5sum {} +"""
            stdin, stdout, stderr = ssh.exec_command(buildCommand)
            time.sleep(15)
            for line in  stdout.readlines():
                local_md5sum += str(line.split(" ")[0])
            return local_md5sum
        except Exception as e:
            LOG.debug("Exception: " + str(e))


    '''
    Method returns the list of details of restored VMs
    '''
    def get_vm_details(self, server_id):
        response = self.servers_client.show_server(server_id)
        LOG.debug("Vm details :"+ str(response))
        return response

    '''
    Method to populate data before full backup
    '''
    def data_populate_before_backup(self, workload_instances, floating_ips_list, backup_size, files_count, mount_points):
        md5sums_dir_before = {}
        for id in range(len(workload_instances)):
            self.md5sums = ""
            LOG.debug("setting floating ip" + (floating_ips_list[id].encode('ascii','ignore')))
            ssh = self.SshRemoteMachineConnectionWithRSAKey(floating_ips_list[id])
            for mount_point in mount_points:
                self.addCustomSizedfilesOnLinux(ssh, mount_point+"/", files_count)
                self.md5sums+=(self.calculatemmd5checksum(ssh, mount_point))

            md5sums_dir_before[str(floating_ips_list[id])] = self.md5sums
            LOG.debug("before backup md5sum for " + floating_ips_list[id].encode('ascii','ignore') + " " +str(self.md5sums))

        LOG.debug("before backup md5sum : " + str(md5sums_dir_before))
        return md5sums_dir_before

    '''
    Method to populate data before full backup
    '''
    def calculate_md5_after_restore(self, workload_instances, floating_ips_list, volumes,mount_points):
        LOG.debug("Calculating md5 sums for :" + str(workload_instances) + "||||" + str(floating_ips_list))
        md5sums_dir_after = {}
        for id in range(len(workload_instances)):
            self.md5sums = ""
            # md5sums_dir_after = {}
            ssh = self.SshRemoteMachineConnectionWithRSAKey(floating_ips_list[id])

            self.execute_command_disk_mount(ssh, floating_ips_list[id],volumes, mount_points)
            for mount_point in mount_points:
                self.md5sums+=(self.calculatemmd5checksum(ssh, mount_point))

            md5sums_dir_after[str(floating_ips_list[id])] = self.md5sums

            LOG.debug("after md5sum for " + floating_ips_list[id].encode('ascii','ignore') + " " +str(self.md5sums))

        LOG.debug("after md5sum : " + str(md5sums_dir_after))
        return md5sums_dir_after


    '''
    Method to create key pair
    '''
    def create_key_pair(self, keypair_name, keypair_cleanup=True):
        foorprint = ""
        key_pairs_list_response = self.keypairs_client.list_keypairs()
        key_pairs = key_pairs_list_response['keypairs']
        for key in key_pairs:
            if str(key['keypair']['name']) == keypair_name:
                self.keypairs_client.delete_keypair(keypair_name)

        keypair_response = self.keypairs_client.create_keypair(name=keypair_name)
        privatekey = keypair_response['keypair']['private_key']
        fingerprint  = keypair_response['keypair']['fingerprint']
        with open(str(keypair_name) + ".pem", 'w+') as f:
            f.write(str(privatekey))
        os.chmod(str(keypair_name) + ".pem", stat.S_IRWXU)
        LOG.debug("keypair fingerprint : " + str(fingerprint))
	if(tvaultconf.cleanup == True and keypair_cleanup == True):
	    self.addCleanup(self.delete_key_pair, keypair_name)
        return fingerprint

    '''
    Method to disassociate floating ip to a server
    '''
    def disassociate_floating_ip_from_server(self, floating_ip, server_id):
	LOG.debug("Disassociation of " + str(floating_ip) + " from " + str(server_id) + " started.")
        set_response = self.servers_client.action(server_id, "removeFloatingIp", address=str(floating_ip))
        return set_response

    '''
    Method to fetch id of given floating ip
    '''
    def get_floatingip_id(self, floating_ip):
	floatingip_id = None
        floatingips = self.network_client.list_floatingips()
        for i in range(len(floatingips['floatingips'])):
            if(str(floatingips['floatingips'][i]['floating_ip_address']) == str(floating_ip)):
                floatingip_id = floatingips['floatingips'][i]['id']
		LOG.debug("floating ip id for :" + str(floating_ip) +" is: " + str(floatingip_id))
        return floatingip_id

    '''
    Method to fetch port id of given floating ip
    '''
    def get_portid_of_floatingip(self, floating_ip):
        port_id = None
        floatingips = self.network_client.list_floatingips()
        for i in range(len(floatingips['floatingips'])):
            if(str(floatingips['floatingips'][i]['floating_ip_address']) == str(floating_ip)):
                port_id = floatingips['floatingips'][i]['port_id']
		LOG.debug("port id for :" + str(floating_ip) +" is: " + str(port_id))
        return port_id


    '''
    Method to get key pair details
    '''
    def get_key_pair_details(self, keypair_name):
        foorprint = ""
        key_pairs_list_response = self.keypairs_client.show_keypair(keypair_name)
        fingerprint  = key_pairs_list_response['keypair']['fingerprint']
        LOG.debug("keypair fingerprint : " + str(fingerprint))
        return fingerprint

    '''Fetch required details of the instances'''
    def get_vms_details_list(self, vm_details_list):
	self.vms_details = []
	for i in range(len(vm_details_list)):
            server_id = vm_details_list[i]['server']['id']
            if len(vm_details_list[i]['server']['addresses'][list(vm_details_list[i]['server']['addresses'].keys())[0]]) == 2:
                floatingip = str(vm_details_list[i]['server']['addresses'][list(vm_details_list[i]['server']['addresses'].keys())[0]][1]['addr'])
            else:
    	        floatingip = None
            tmp_json = { 'id': server_id,
                    'name': vm_details_list[i]['server']['name'],
                    'network_name': list(vm_details_list[i]['server']['addresses'].keys())[0],
                    'keypair': vm_details_list[i]['server']['key_name'],
                    'floating_ip': floatingip,
                    'vm_status': vm_details_list[i]['server']['status'],
                    'vm_power_status': vm_details_list[i]['server']['OS-EXT-STS:vm_state'],
                    'availability_zone': vm_details_list[i]['server']['OS-EXT-AZ:availability_zone'],
                    'flavor_id': vm_details_list[i]['server']['flavor']['id']                    
                    }
	    self.vms_details.append(tmp_json)
	return self.vms_details

    '''floating ip availability'''
    def get_floating_ip_status(self, ip):
        floating_ip_status = self.floating_ips_client.show_floating_ip(ip)
        LOG.debug("floating ip details fetched: " + str(floating_ip_status))

    '''get network name  by id'''
    def get_net_name(self, network_id):
        return str(self.compute_networks_client.show_network(network_id).items()[0][1]['label'])

    '''get subnet id'''
    def get_subnet_id(self, network_id):
        subnet_list = self.subnets_client.list_subnets().items()[0][1]
        for subnet in subnet_list:
            if subnet['network_id'] == network_id:
                return subnet['id']

    '''delete key'''
    def delete_key_pair(self, keypair_name):
        key_pairs_list_response = self.keypairs_client.list_keypairs()
        key_pairs = key_pairs_list_response['keypairs']
        for key in key_pairs:
            if str(key['keypair']['name']) == keypair_name:
                self.keypairs_client.delete_keypair(keypair_name)

    '''delete security group'''
    def delete_security_group(self, security_group_id):
	try:
            self.security_groups_client.delete_security_group(security_group_id)
	except lib_exc.NotFound:
            return

    '''delete flavor'''
    def delete_flavor(self, flavor_id):
	try:
            self.flavors_client.delete_flavor(flavor_id)
	except lib_exc.NotFound:
            return

    '''get port_id from floating_ip'''
    def get_port_id(self, fixed_ip):
        ports_list = []
        ports_list = self.get_port_list()
        for port in ports_list['ports']:
            if str(port['fixed_ips'][0]['ip_address']) == str(fixed_ip):
                return str(port['id'])

    '''delete port'''
    def delete_port(self, server_id):
        ports = []
        internal_network_name = str((self.get_vm_details(server_id)['server']['addresses'].keys()[0]))
        fixed_ip = str((self.get_vm_details(server_id)['server']['addresses'][internal_network_name][0]['addr']))
        ports.append(self.get_port_id(fixed_ip))
	LOG.debug("Port deletion for " + str(ports) + " started.")
        self.delete_ports(ports)

    '''create_security_group'''
    def create_security_group(self, name, secgrp_cleanup=True):
        security_group_id = self.security_groups_client.create_security_group(name=name, description = "test_description")['security_group']['id']
        self.security_group_rules_client.create_security_group_rule(parent_group_id = str(security_group_id), ip_protocol = "TCP", from_port = 1, to_port = 40000)
        self.security_group_rules_client.create_security_group_rule(parent_group_id = str(security_group_id), ip_protocol = "UDP", from_port = 1, to_port = 50000)
	self.security_group_rules_client.create_security_group_rule(parent_group_id = str(security_group_id), ip_protocol = "TCP", from_port = 22, to_port = 22)
        security_group_details = (self.security_groups_client.show_security_group(str(security_group_id)))
        LOG.debug(security_group_details)
	if(tvaultconf.cleanup == True and secgrp_cleanup == True):
	    self.addCleanup(self.delete_security_group, security_group_id)
        return security_group_details

    '''get_security_group_details'''
    def get_security_group_details(self, security_group_id):
        security_group_details = (self.security_groups_client.show_security_group(str(security_group_id)))
        LOG.debug(security_group_details)
        return security_group_details
	
	
    '''get_security_group_id_by_name'''
    def get_security_group_id_by_name(self, security_group_name):
	security_group_id = ""
	security_groups_list = self.security_groups_client.list_security_groups()['security_groups']
	LOG.debug("Security groups list" + str(security_groups_list))
	for security_group in security_groups_list:
	    if security_group['name'] == security_group_name:
		security_group_id = security_group['id']
	if security_group_id!= "":
	    return security_group_id
	else:
	    return None

    '''create_flavor'''
    def create_flavor(self, name, flavor_cleanup=True):
        flavor_id = self.flavors_client.create_flavor(name=name, disk = 20, vcpus = 2  , ram = 1024 )['flavor']['id']
        LOG.debug("flavor id" + str(flavor_id))
	if(tvaultconf.cleanup == True and flavor_cleanup == True):
	    self.addCleanup(self.delete_flavor, flavor_id)
        return flavor_id

    '''
    Method to get the flavor id corresponding to the given flavor name
    '''
    def get_flavor_id(self, flavor_name):
	flavor_id = 0
        flavor_list = self.flavors_client.list_flavors()['flavors']
        LOG.debug("Flavor list: " + str(flavor_list))
	for i in range(0, len(flavor_list)):
	     if(flavor_list[i]['name'] == flavor_name):
	          flavor_id = flavor_list[i]['id']
        return flavor_id

    '''Fetch flavor details of particular flavor id'''
    def get_flavor_details(self, flavor_id):
        flavor_resp = self.flavors_client.show_flavor(flavor_id)['flavor']
        flavor_details = {'ram': flavor_resp['ram'],
                          'OS-FLV-DISABLED:disabled': flavor_resp['OS-FLV-DISABLED:disabled'],
                          'vcpus': flavor_resp['vcpus'],
                          'swap': flavor_resp['swap'],
                          'os-flavor-access:is_public': flavor_resp['os-flavor-access:is_public'],
                          'rxtx_factor': flavor_resp['rxtx_factor'],
                          'OS-FLV-EXT-DATA:ephemeral': flavor_resp['OS-FLV-EXT-DATA:ephemeral'],
                          'disk': flavor_resp['disk']}
        return flavor_details

