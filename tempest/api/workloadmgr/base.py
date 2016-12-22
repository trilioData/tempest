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

from oslo_log import log as logging

from tempest import config
import tempest.test
#from testtools import testcase
#from tempest import api
#from tempest.common import compute
import time
from tempest.common import waiters
from oslo_config import cfg
#from random import choice
#from string import ascii_lowercase
#import unittest
from tempest_lib import exceptions as lib_exc
import datetime
from tempest import tvaultconf
import os

CONF = config.CONF
LOG = logging.getLogger(__name__)


class BaseWorkloadmgrTest(tempest.test.BaseTestCase):

    _api_version = 2
    force_tenant_isolation = False
    credentials = ['primary']
    
    @classmethod
    def setup_clients(cls):
        super(BaseWorkloadmgrTest, cls).setup_clients()
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
    @classmethod
    def getWorkloadStatus(cls, workload_id):
        resp, body =cls.wlm_client.client.get("/workloads/"+workload_id)
        workload_status = body['workload']['status']
        LOG.debug("#### workloadid: %s , operation:show_workload" % workload_id)
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return workload_status

    '''
    Method returns the current status of a given snapshot
    '''
    @classmethod
    def getSnapshotStatus(cls, workload_id, snapshot_id):
        resp, body = cls.wlm_client.client.get("/workloads/"+workload_id+"/snapshots/"+snapshot_id)
        snapshot_status = body['snapshot']['status']
        LOG.debug("#### workloadid: %s ,snapshot_id: %s , operation:show_snapshot" % (workload_id, snapshot_id))
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return snapshot_status

    '''
    Method returns the current status of a given restore
    '''
    @classmethod
    def getRestoreStatus(cls, workload_id, snapshot_id, restore_id):
        resp, body = cls.wlm_client.client.get("/workloads/"+workload_id+"/snapshots/"+snapshot_id+"/restores/"+restore_id)
        restore_status = body['restore']['status']
        LOG.debug("#### workloadid: %s ,snapshot_id: %s, restore_id: %s, operation: show_restore" % (workload_id, snapshot_id, restore_id))
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return restore_status
    
    '''
    Method returns the schedule status of a given workload 
    '''
    @classmethod
    def getSchedulerStatus(cls, workload_id):
        resp, body =cls.wlm_client.client.get("/workloads/"+workload_id)
        schedule_status = body['workload']['jobschedule']['enabled']
        LOG.debug("#### workloadid: %s , operation:show_workload" % workload_id)
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return schedule_status
    
    '''
    Method returns the Retention Policy Type status of a given workload
    '''
    @classmethod
    def getRetentionPolicyTypeStatus(cls, workload_id):
        resp, body =cls.wlm_client.client.get("/workloads/"+workload_id)
        retention_policy_type = body['workload']['jobschedule']['retention_policy_type']
        LOG.debug("#### workloadid: %s , operation:show_workload" % workload_id)
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return retention_policy_type
        
    '''
    Method returns the Retention Policy Value of a given workload
    '''
    @classmethod
    def getRetentionPolicyValueStatus(cls, workload_id):
        resp, body =cls.wlm_client.client.get("/workloads/"+workload_id)
        retention_policy_value = body['workload']['jobschedule']['retention_policy_value']
        LOG.debug("#### workloadid: %s , operation:show_workload" % workload_id)
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return retention_policy_value

    '''
    Method returns the Full Backup Interval status of a given workload
    '''
    @classmethod
    def getFullBackupIntervalStatus(cls, workload_id):
        resp, body =cls.wlm_client.client.get("/workloads/"+workload_id)
        Full_Backup_Interval_Value = body['workload']['jobschedule']['fullbackup_interval']
        LOG.debug("#### workloadid: %s , operation:show_workload" % workload_id)
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return Full_Backup_Interval_Value
    
    '''
    Method raises exception if snapshot is not successful
    '''
    @classmethod
    def assertSnapshotSuccessful(cls, workload_id, snapshot_id):
        snapshot_status = cls.getSnapshotStatus(workload_id, snapshot_id)
        cls.assertEqual(snapshot_status, "available")
    
    '''
    Method raises exception if restore is not successful
    '''
    @classmethod
    def assertRestoreSuccessful(cls, workload_id, snapshot_id, restore_id):
        restore_status = cls.getRestoreStatus(workload_id, snapshot_id, restore_id)
        cls.assertEqual(restore_status, "available")
    
    '''
    Method raises exception if scheduler is not enabled for a given workload
    '''
    @classmethod
    def assertSchedulerEnabled(cls, workload_id):
        scheduler_status = cls.getSchedulerStatus(workload_id)
        cls.assertEqual(scheduler_status, "true")

    '''
    Method returns the Instance ID of a new VM instance created
    '''
    def create_vm(self, vm_cleanup=True):
        if(tvaultconf.vms_from_file):
            flag=0
            flag=self.is_vm_available()
            if(flag != 0):
                server_id=self.read_vm_id()
            else:
                server=self.servers_client.create_server(name="tempest-test-vm", imageRef=CONF.compute.image_ref, flavorRef=CONF.compute.flavor_ref)
                server_id= server['server']['id']
                waiters.wait_for_server_status(self.servers_client, server_id, status='ACTIVE')
        else:
            server=self.servers_client.create_server(name="tempest-test-vm", imageRef=CONF.compute.image_ref, flavorRef=CONF.compute.flavor_ref)
            server_id= server['server']['id']
            waiters.wait_for_server_status(self.servers_client, server_id, status='ACTIVE')
            #self.servers_client.stop_server(server_id)
            #waiters.wait_for_server_status(self.servers_client, server_id, status='SHUTOFF')
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
                    server=self.servers_client.create_server(name="tempest-test-vm", imageRef=CONF.compute.image_ref, flavorRef=CONF.compute.flavor_ref)
                    server_id=server['server']['id']
                    waiters.wait_for_server_status(self.servers_client, server['server']['id'], status='ACTIVE')
            else:
                server=self.servers_client.create_server(name="tempest-test-vm", imageRef=CONF.compute.image_ref, flavorRef=CONF.compute.flavor_ref)
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
    @classmethod
    def delete_vm(cls, server_id):
        try:
            body = cls.servers_client.show_server(server_id)['server']
            cls.servers_client.delete_server(server_id)
            waiters.wait_for_server_termination(cls.servers_client, server_id)
        except lib_exc.NotFound:
            return
    
    '''
    Method deletes the given VM instances list
    '''
    @classmethod
    def delete_vms(cls, instances):
        totalVms = len(instances)
        for vm in range(0,totalVms):
            try:
                cls.servers_client.delete_server(instances[vm])
                waiters.wait_for_server_termination(cls.servers_client, instances[vm])
            except Exception as e:
                pass
        LOG.debug('DeletedVms: %s' % instances)

    '''
    Method creates a new volume and returns Volume ID
    '''
    def create_volume(self, size, volume_type_id, volume_cleanup=True):
        if(tvaultconf.volumes_from_file):
            flag=0
            flag=self.is_volume_available()
            if(flag != 0):
                volume_id=self.read_volume_id()
            else:
                volume = self.volumes_client.create_volume(size=size, volume_type=volume_type_id)
                volume_id= volume['volume']['id']
                waiters.wait_for_volume_status(self.volumes_client,
                                       volume_id, 'available')
        else:
            volume = self.volumes_client.create_volume(size=size, volume_type=volume_type_id)
            volume_id= volume['volume']['id']
            waiters.wait_for_volume_status(self.volumes_client,
                                       volume_id, 'available')
        if(tvaultconf.cleanup == True and volume_cleanup == True):
            self.addCleanup(self.delete_volume, volume_id)
        return volume_id

    '''
    Method deletes a given volume
    '''
    @classmethod
    def delete_volume(cls, volume_id):
        try:
            cls.volumes_client.delete_volume(volume_id)
        except Exception as e:
            return
    
    '''
    Method deletes a given volume snapshot
    '''
    @classmethod
    def delete_volume_snapshot(cls, volume_snapshot_id):
        try:
            cls.snapshots_extensions_client.delete_snapshot(volume_snapshot_id)
        except Exception as e:
            return
        
    '''
    Method deletes a list of volume snapshots
    '''
    @classmethod
    def delete_volume_snapshots(cls, volume_snapshots):
        for snapshot in range(0, len(volume_snapshots)):
            try:
                cls.volumes_client.delete_volume(volume_snapshots[snapshot])
                LOG.debug('Snapshot delete operation completed %s' % volume_snapshots[snapshot])
            except Exception as e:
                LOG.error("Exception: " + str(e))
        
    '''
    Method to return list of available volume snapshots
    '''
    @classmethod
    def get_available_volume_snapshots(cls):
        volume_snapshots = []
        resp = cls.snapshots_extensions_client.list_snapshots()
        for i in range(0,len(resp['snapshots'])):
            volume_snapshots.append(resp['snapshots'][i]['id'])
        LOG.debug("Volume snapshots: " + str(volume_snapshots))
        return volume_snapshots
    
    '''
    Method returns the list of attached volumes to a given VM instance
    '''
    @classmethod
    def get_attached_volumes(cls, server_id):
        server = cls.servers_client.show_server(server_id)['server']
        volumes=server['os-extended-volumes:volumes_attached']
        volume_list = []
        for volume in volumes:
            volume_list.append(volume['id']);
        LOG.debug("Attached volumes: "+ str(volume_list))
        return volume_list
        
    '''
    Method deletes the given volumes list
    '''
    @classmethod
    def delete_volumes(cls, volumes):
        total_volumes = len(volumes)
        for volume in range(0, total_volumes):
            try:
                cls.volumes_client.delete_volume(volumes[volume])
                LOG.debug('Volume delete operation completed %s' % volume)
            except Exception as e:
                pass
    
    '''
    Method attaches given volume to given VM instance
    '''
    def attach_volume(self, volume_id, server_id, device="/dev/vdb", attach_cleanup=True):
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
    @classmethod
    def detach_volume(cls, server_id, volume_id):
        #cls.volumes_client.detach_volume(volume_id)
        #waiters.wait_for_volume_status(cls.volumes_client,
        #                               volume_id, 'available')
        try:
            body=cls.volumes_client.show_volume(volume_id)['volume']
            cls.servers_client.detach_volume(server_id, volume_id)
            cls.volumes_client.wait_for_volume_status(volume_id, 'available')
        except lib_exc.NotFound:
            return
    
    '''
    Method to detach given list of volumes
    '''
    @classmethod
    def detach_volumes(cls, volumes):
        total_volumes = len(volumes)
        for volume in range(0, total_volumes):
            cls.volumes_client.detach_volume(volumes[volume])
            LOG.debug('Volume detach operation completed %s' % volume)
            waiters.wait_for_volume_status(cls.volumes_client,
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
                ts=str(datetime.datetime.now())
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
                ts=str(datetime.datetime.now())
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
    @classmethod
    def workload_delete(cls, workload_id):
        try:
            resp, body = cls.wlm_client.client.delete("/workloads/"+workload_id)
            LOG.debug("#### workloadid: %s , operation: workload_delete" % workload_id)
            LOG.debug("Response:"+ str(resp.content))
        except Exception as e:
            pass
        LOG.debug('WorkloadDeleted: %s' % workload_id)

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
        #self.wait_for_workload_tobe_available(workload_id)
        if(tvaultconf.cleanup == True and snapshot_cleanup == True):
            self.addCleanup(self.snapshot_delete,workload_id, snapshot_id)
        return snapshot_id

    '''
    Method resets the given workload
    '''
    @classmethod
    def workload_reset(cls, workload_id):
        cls.wait_for_workload_tobe_available(workload_id)
        resp, body = cls.wlm_client.client.post("/workloads/"+workload_id+"/reset")
        LOG.debug("#### workloadid: %s, operation: workload-reset " % workload_id)
        LOG.debug("Response:"+ str(resp.content))
        LOG.debug("Response code:"+ str(resp.status_code))
        if (resp.status_code != 202):
            resp.raise_for_status()

    '''
    Method to wait until the workload is available
    '''
    @classmethod
    def wait_for_workload_tobe_available(cls, workload_id):
        status = "available"
        start_time = int(time.time())
        LOG.debug('Checking workload status')
        while ( status != cls.getWorkloadStatus(workload_id)):
            if ( cls.getWorkloadStatus(workload_id) == 'error'):
                LOG.debug('workload status is: %s , workload create failed' % cls.getWorkloadStatus(workload_id))
                raise Exception("Workload creation failed")
            LOG.debug('workload status is: %s , sleeping for 30 sec' % cls.getWorkloadStatus(workload_id))
            time.sleep(30)
        LOG.debug('workload status of workload %s: %s' % (workload_id, cls.getWorkloadStatus(workload_id)))

    '''
    Method to check if snapshot is successful
    '''
    @classmethod
    def is_snapshot_successful(cls, workload_id, snapshot_id):
        is_successful= "False"
        if(cls.getSnapshotStatus(workload_id, snapshot_id) == 'available'):
            LOG.debug('snapshot successful: %s' % snapshot_id)
            is_successful = "True"
        return is_successful

    '''
    Method deletes a given snapshot
    '''
    @classmethod
    def snapshot_delete(cls, workload_id, snapshot_id):
        cls.wait_for_workload_tobe_available(workload_id)
        resp, body = cls.wlm_client.client.delete("/snapshots/"+str(snapshot_id))
        LOG.debug("#### workloadid: %s ,snapshot_id: %s  , Operation: snapshot_delete" % (workload_id, snapshot_id))
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 202):
            resp.raise_for_status()
        cls.wait_for_workload_tobe_available(workload_id)
        LOG.debug('SnapshotDeleted: %s' % workload_id)

    '''
    Method creates one click restore for a given snapshot and returns the restore id
    '''
    def snapshot_restore(self, workload_id, snapshot_id, restore_name="", restore_cleanup=True):
        LOG.debug("At the start of snapshot_restore method")
        if(restore_name == ""):
            restore_name = "Tempest test restore"
        payload={"restore": {"options": {"description": "Tempest test restore",
                                           "oneclickrestore": True,
                                           "vmware": {},
                                           "openstack": {"instances": [], "zone": ""},
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
            self.addCleanup(self.restore_delete, workload_id, snapshot_id, restore_id)
            self.addCleanup(self.delete_restored_vms, workload_id, snapshot_id, restore_id)
        return restore_id

    '''
    Method creates selective restore for a given snapshot and returns the restore id
    '''
    def snapshot_selective_restore(self, workload_id, snapshot_id, restore_name="", restore_cleanup=True):
        LOG.debug("At the start of snapshot_selective_restore method")
        if(restore_name ==""):
            restore_name =  "Tempest test restore"
        payload={"restore": {"options": {"description": "Tempest test restore",
                                           "oneclickrestore": False,
                                           "vmware": {},
                                           "openstack": {"instances": [], "zone": ""},
                                           "type": "openstack",
                                           "restore_options": {},
                                           "name": restore_name},
                "name": restore_name,
                "description": "Tempest test restore"}}
        LOG.debug("In snapshot_restore method, before calling waitforsnapshot method")
        self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
        LOG.debug("After returning from waitfor snapshot")
        resp, body = self.wlm_client.client.post("/workloads/"+workload_id+"/snapshots/"+snapshot_id+"/restores",json=payload)
        restore_id = body['restore']['id']
        LOG.debug("#### workloadid: %s ,snapshot_id: %s , restore_id: %s , operation: snapshot_restore" % (workload_id, snapshot_id, restore_id))
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 202):
            resp.raise_for_status()
        LOG.debug('Restore of snapshot %s scheduled succesffuly' % snapshot_id)
        #self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
        if(tvaultconf.cleanup == True and restore_cleanup == True):
            self.addCleanup(self.restore_delete, workload_id, snapshot_id, restore_id)
            self.addCleanup(self.delete_restored_vms, workload_id, snapshot_id, restore_id)
        return restore_id
   
    '''
    Method returns the list of restored VMs
    '''
    @classmethod
    def get_restored_vm_list(cls, restore_id):
        resp, body = cls.wlm_client.client.get("/restores/"+restore_id)
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
    @classmethod
    def get_restored_volume_list(cls, restore_id):
        resp, body = cls.wlm_client.client.get("/restores/"+restore_id)
        LOG.debug("Body: " + str(body))
        LOG.debug("Response: " + str(resp))
        instances= body['restore']['instances']
        restore_volumes = []
        for instance in instances:
            LOG.debug("instance:"+ instance['id'])
            restore_volumes.extend(cls.get_attached_volumes(instance['id']))
        LOG.debug("restored volume list:"+ str(restore_volumes))
        return restore_volumes

    '''
    Method deletes the given restored VMs and volumes
    '''
    @classmethod
    def delete_restored_vms(cls, restore_vms, restore_volumes):        
        cls.delete_vms(restore_vms)
        cls.delete_volumes(restore_volumes)

    '''
    Method to wait until the snapshot is available
    '''
    @classmethod
    def wait_for_snapshot_tobe_available(cls, workload_id, snapshot_id):
        status = "available"
        LOG.debug('Checking snapshot status')
        while (status != cls.getSnapshotStatus(workload_id, snapshot_id)):
            if(cls.getSnapshotStatus(workload_id, snapshot_id) == 'error'):
                LOG.debug('Snapshot status is: %s' % cls.getSnapshotStatus(workload_id, snapshot_id))
                raise Exception("Snapshot creation failed")            
            LOG.debug('Snapshot status is: %s' % cls.getSnapshotStatus(workload_id, snapshot_id))
            time.sleep(10)           
        LOG.debug('Final Status of snapshot: %s' % (cls.getSnapshotStatus(workload_id, snapshot_id)))
        return status
    
    '''
    Method to check if restore is successful
    '''
    @classmethod
    def is_restore_successful(cls, workload_id, snapshot_id, restore_id):
        is_successful= "False"
        if(cls.getRestoreStatus(workload_id, snapshot_id, restore_id) == 'available'):
            is_successful = "True"
        return is_successful

    '''
    Method returns if scheduler is running for a given workload
    '''
    @classmethod
    def is_schedule_running(cls,workload_id):
        is_running= False
        snapshot_list=cls.getSnapshotList(workload_id)
        for i in range (0,(len(snapshot_list))):
            FMT = "%Y-%m-%dT%H:%M:%S.000000"
            if (i==0):
                SnapshotCreateTime = cls.getSnapshotCreateTimeInfo(snapshot_list[i])
                LOG.debug('snapshot create time is: %s' % SnapshotCreateTime)
                SnapshotNameInfo = cls.getSnapshotNameInfo(snapshot_list[i])
                if(SnapshotNameInfo == 'jobscheduler'):
                    is_running = True
                    LOG.debug('snapshot is running: %s' % snapshot_list[i])
                    cls.wait_for_workload_tobe_available(workload_id)
                    cls.assertEqual(cls.getSnapshotStatus(workload_id, snapshot_list[i]), "available")
                else:
                    LOG.debug('snapshot is not running: %s' % snapshot_list[i])
                    is_running = False
            else:
                SnapshotCreateTime = cls.getSnapshotCreateTimeInfo(snapshot_list[i])
                SnapshotCreateTime1 = cls.getSnapshotCreateTimeInfo(snapshot_list[i-1])
                tdelta = datetime.strptime(SnapshotCreateTime, FMT) - datetime.strptime(SnapshotCreateTime1, FMT)
                LOG.debug('Time Interval Between Two snapshot is: %s' % str(tdelta))
                SnapshotNameInfo = cls.getSnapshotNameInfo(snapshot_list[i])
                if(SnapshotNameInfo == 'jobscheduler' and (str(tdelta)=="1:00:00")):
                    is_running = True
                    LOG.debug('snapshot is running: %s' %str(tdelta))
                    cls.wait_for_workload_tobe_available(workload_id)
                    cls.assertEqual(cls.getSnapshotStatus(workload_id, snapshot_list[i]), "available")
                else:
                    LOG.debug('snapshot is not running: %s' % snapshot_list[i])
                    is_running = False
        return is_running

        
    '''
    Method to delete a given restore
    '''
    @classmethod
    def restore_delete(cls, workload_id, snapshot_id, restore_id):
        cls.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
        resp, body = cls.wlm_client.client.delete("/workloads/"+workload_id+"/snapshots/"+snapshot_id+"/restores/"+restore_id)
        LOG.debug("#### workloadid: %s ,snapshot_id: %s  , Operation: snapshot_delete" % (workload_id, snapshot_id))
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 202):
            resp.raise_for_status()
        cls.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
        LOG.debug('SnapshotDeleted: %s' % workload_id)

    '''
    Method to check if VM details are available in file
    '''
    @classmethod
    def is_vm_available(cls):
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
    @classmethod
    def read_vm_id(cls):
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
    @classmethod
    def is_volume_available(cls):
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
    @classmethod
    def read_volume_id(cls):
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
    @classmethod
    def is_workload_available(cls):
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
    @classmethod
    def read_workload_id(cls):
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
    @classmethod
    def verifyScheduleTest(cls,workload_id):
        tvaultconf.count = tvaultconf.count + 1
        LOG.debug("tvaultconf.count value is:%s" % tvaultconf.count)
        f = open(tvaultconf.schedule_report_file, "a")
        if (cls.is_schedule_running(workload_id)):
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
    @classmethod
    def get_port_list(cls):
        port_list = cls.network_client.list_ports()
        LOG.debug("Port List: " + str(port_list))
        return port_list
    
    '''
    Method to delete list of ports
    '''
    @classmethod
    def delete_ports(cls, port_list):
        for i in range(0,len(port_list)):
            port_delete = cls.network_client.delete_port(port_list[i])
            LOG.debug("Port %s status %s" % (port_list[i], port_delete))

    '''
    Method returns the snapshot list information
    '''
    @classmethod
    def getSnapshotList(cls,workload_id='none'):
        resp, body = cls.wlm_client.client.get("/snapshots?workload_id="+workload_id)
        snapshot_list = []
        for i in range(0,len(body['snapshots'])):
            snapshot_list.append(body['snapshots'][i]['id'])
            LOG.debug('snapshot id is: %s' % snapshot_list[i])
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
           resp.raise_for_status()
        return snapshot_list


    '''
    Method returns the snapshot create time information
    '''
    @classmethod
    def getSnapshotCreateTimeInfo(cls,snapshot_id='none'):
        resp, body = cls.wlm_client.client.get("/snapshots/"+snapshot_id)
        snapshot_create_time_info = body['snapshot']['created_at']
        LOG.debug('snapshot create time is: %s' % snapshot_create_time_info)
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
           resp.raise_for_status()
        return snapshot_create_time_info


    '''
    Method returns the snapshot name information
    '''
    @classmethod
    def getSnapshotNameInfo(cls,snapshot_id='none'):
        resp, body = cls.wlm_client.client.get("/snapshots/"+snapshot_id)
        snapshot_name_info = body['snapshot']['name']
        LOG.debug('snapshot name is: %s' % snapshot_name_info)
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
           resp.raise_for_status()
        return snapshot_name_info

    '''
    Method returns the snapshot type information
    '''
    @classmethod
    def getSnapshotTypeInfo(cls,snapshot_id='none'):
        resp, body = cls.wlm_client.client.get("/snapshots/"+snapshot_id)
        snapshot_type_info = body['snapshot']['snapshot_type']
        LOG.debug('snapshot type is : %s' % snapshot_type_info)
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
           resp.raise_for_status()
        return snapshot_type_info
