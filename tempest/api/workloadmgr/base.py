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

import time
import json
import paramiko
import os
import stat
import requests
import re
import collections
import base64

from oslo_log import log as logging
from tempest import config
import tempest.test
from tempest.common import waiters
from oslo_config import cfg
from tempest.lib import exceptions as lib_exc
from datetime import datetime
from datetime import timedelta
from tempest import tvaultconf
from tempest import command_argument_string
from tempest.util import cli_parser
from tempest.util import query_data

CONF = config.CONF
LOG = logging.getLogger(__name__)


class BaseWorkloadmgrTest(tempest.test.BaseTestCase):

    _api_version = 2
    force_tenant_isolation = False
    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(BaseWorkloadmgrTest, cls).setup_clients()
        cls.subnets_client = cls.os_primary.subnets_client
        cls.wlm_client = cls.os_primary.wlm_client
        cls.servers_client = cls.os_primary.servers_client
        cls.flavors_client = cls.os_primary.flavors_client
        cls.floating_ips_client = cls.os_primary.floating_ips_client
        cls.keypairs_client = cls.os_primary.keypairs_client
        cls.security_group_rules_client = cls.os_primary.security_group_rules_client
        cls.security_groups_client = cls.os_primary.security_groups_client
        cls.routers_client = cls.os_primary.routers_client
        cls.volumes_extensions_client = cls.os_primary.volumes_extensions_client
        cls.snapshots_extensions_client = cls.os_primary.snapshots_extensions_client
        cls.ports_client = cls.os_primary.ports_client
        cls.networks_client = cls.os_primary.networks_client

        cls.volumes_client = cls.os_primary.volumes_v2_client
        cls.volumes_client.service = 'volumev2'

        if CONF.identity_feature_enabled.api_v2:
            cls.identity_client = cls.os_primary.identity_client
        else:
            cls.identity_client = cls.os_primary.identity_v3_client

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
        resp, body = self.wlm_client.client.get("/workloads/" + workload_id)
        workload_status = body['workload']['status']
        LOG.debug("#### workloadid: %s , operation:show_workload" %
                  workload_id)
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return workload_status

    '''
    Method returns the current status of a given snapshot
    '''

    def getSnapshotStatus(self, workload_id, snapshot_id):
        resp, body = self.wlm_client.client.get(
            "/workloads/" + workload_id + "/snapshots/" + snapshot_id)
        snapshot_status = body['snapshot']['status']
        LOG.debug(
            "#### workloadid: %s ,snapshot_id: %s , operation:show_snapshot" %
            (workload_id, snapshot_id))
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return snapshot_status

    '''
    Method returns the current status of a given restore
    '''

    def getRestoreStatus(self, workload_id, snapshot_id, restore_id):
        resp, body = self.wlm_client.client.get(
            "/workloads/" + str(workload_id) + "/snapshots/" + str(snapshot_id) + "/restores/" + str(restore_id))
        restore_status = body['restore']['status']
        LOG.debug(
            "#### workloadid: %s ,snapshot_id: %s, restore_id: %s, operation: show_restore" %
            (workload_id, snapshot_id, restore_id))
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return restore_status

    '''
    Method returns the schedule status of a given workload
    '''

    def getSchedulerStatus(self, workload_id):
        resp, body = self.wlm_client.client.get("/workloads/" + workload_id)
        schedule_status = body['workload']['jobschedule']['enabled']
        LOG.debug("#### workloadid: %s , operation:show_workload" %
                  workload_id)
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return schedule_status

    '''
    Method returns the Retention Policy Type status of a given workload
    '''

    def getRetentionPolicyTypeStatus(self, workload_id):
        resp, body = self.wlm_client.client.get("/workloads/" + workload_id)
        retention_policy_type = body['workload']['jobschedule']['retention_policy_type']
        LOG.debug("#### workloadid: %s , operation:show_workload" %
                  workload_id)
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return retention_policy_type

    '''
    Method returns the Retention Policy Value of a given workload
    '''

    def getRetentionPolicyValueStatus(self, workload_id):
        resp, body = self.wlm_client.client.get("/workloads/" + workload_id)
        retention_policy_value = body['workload']['jobschedule']['retention_policy_value']
        LOG.debug("#### workloadid: %s , operation:show_workload" %
                  workload_id)
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return retention_policy_value

    '''
    Method returns the Full Backup Interval status of a given workload
    '''

    def getFullBackupIntervalStatus(self, workload_id):
        resp, body = self.wlm_client.client.get("/workloads/" + workload_id)
        Full_Backup_Interval_Value = body['workload']['jobschedule']['fullbackup_interval']
        LOG.debug("#### workloadid: %s , operation:show_workload" %
                  workload_id)
        LOG.debug("Response:" + str(resp.content))
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
        restore_status = self.getRestoreStatus(
            workload_id, snapshot_id, restore_id)
        self.assertEqual(restore_status, "available")

    '''
    Method raises exception if scheduler is not enabled for a given workload
    '''

    def assertSchedulerEnabled(self, workload_id):
        scheduler_status = self.getSchedulerStatus(workload_id)
        self.assertEqual(scheduler_status, "true")

    '''
    Method to update image metadata
    Commenting this method, as images_client not available. When required, can revisit and fix it
    '''
#    def update_image(self, image_id, meta):
#        try:
#            response = self.images_client.update_image_metadata(image_id, meta)
#            LOG.debug("image_update" + str(response))
#            return True
#        except Exception as e:
#            LOG.error("Excetpion in base.py : " + str(e))
#            return False

    '''
    Method returns the Instance ID of a new VM instance created
    '''
    def create_vm(self,
                  vm_cleanup=True,
                  vm_name="",
                  security_group_id="default",
                  flavor_id=CONF.compute.flavor_ref,
                  key_pair="",
                  key_name=tvaultconf.key_pair_name,
                  networkid=[{'uuid': CONF.network.internal_network_id}],
                  image_id=CONF.compute.image_ref,
                  block_mapping_data=[],
                  user_data="NULL",
                  a_zone=CONF.compute.vm_availability_zone):
        if(user_data != "NULL"):
            with open(user_data,'rb') as tmp_userdata:
                user_data=base64.b64encode(tmp_userdata.read())
        else:
            user_data=base64.b64encode(b' ')
        if(vm_name == ""):
            ts = str(datetime.now())
            vm_name = "Tempest_Test_Vm" + ts.replace('.', '-')
        if(tvaultconf.vms_from_file and self.is_vm_available()):
            server_id = self.read_vm_id()
        else:
            if (len(block_mapping_data) > 0 and key_pair != ""):
                server = self.servers_client.create_server(
                    name=vm_name,
                    security_groups=[
                        {
                            "name": security_group_id}],
                    imageRef="",
                    flavorRef=flavor_id,
                    networks=networkid,
                    key_name=key_name,
                    block_device_mapping_v2=block_mapping_data,
                    user_data=user_data,
                    availability_zone=a_zone)
            elif (len(block_mapping_data) > 0 and key_pair == ""):
                server = self.servers_client.create_server(
                    name=vm_name,
                    security_groups=[
                        {
                            "name": security_group_id}],
                    imageRef=image_id,
                    flavorRef=flavor_id,
                    networks=networkid,
                    block_device_mapping_v2=block_mapping_data,
                    user_data=user_data,
                    availability_zone=a_zone)
            elif (key_pair != ""):
                server = self.servers_client.create_server(
                    name=vm_name,
                    security_groups=[
                        {
                            "name": security_group_id}],
                    imageRef=image_id,
                    flavorRef=flavor_id,
                    networks=networkid,
                    user_data=user_data,
                    key_name=key_name,
                    availability_zone=a_zone)
            else:
                server = self.servers_client.create_server(
                    name=vm_name,
                    security_groups=[
                        {
                            "name": security_group_id}],
                    imageRef=image_id,
                    flavorRef=flavor_id,
                    networks=networkid,
                    user_data=user_data,
                    availability_zone=a_zone)
            server_id = server['server']['id']
            waiters.wait_for_server_status(
                self.servers_client, server_id, status='ACTIVE')
        if(tvaultconf.cleanup and vm_cleanup):
            self.addCleanup(self.delete_vm, server_id)
        return server_id

    '''
    Method returns the Instance IDs of the new VM instances created
    '''

    def create_vms(self, totalVms):
        instances = []
        for vm in range(0, totalVms):
            if(tvaultconf.vms_from_file):
                flag = 0
                flag = self.is_vm_available()
                if(flag != 0):
                    server_id = self.read_vm_id()
                else:
                    server = self.servers_client.create_server(
                        name="tempest-test-vm",
                        imageRef=CONF.compute.image_ref,
                        flavorRef=CONF.compute.flavor_ref,
                        key_name=tvaultconf.key_pair_name)
                    server_id = server['server']['id']
                    waiters.wait_for_server_status(
                        self.servers_client, server['server']['id'], status='ACTIVE')
            else:
                server = self.servers_client.create_server(
                    name="tempest-test-vm",
                    imageRef=CONF.compute.image_ref,
                    flavorRef=CONF.compute.flavor_ref,
                    key_name=tvaultconf.key_pair_name)
                # instances.append(server['server']['id'])
                server_id = server['server']['id']
                waiters.wait_for_server_status(
                    self.servers_client, server['server']['id'], status='ACTIVE')
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
        for vm in range(0, totalVms):
            try:
                self.delete_vm(instances[vm])
            except Exception as e:
                pass
        LOG.debug('DeletedVms: %s' % instances)

    '''
    Method creates a new volume and returns Volume ID
    '''

    def create_volume(
        self,
        size=CONF.volume.volume_size,
        volume_type_id=CONF.volume.volume_type_id,
        image_id="",
        az_name=CONF.volume.volume_availability_zone,
        volume_cleanup=True):
        if(tvaultconf.volumes_from_file):
            flag = 0
            flag = self.is_volume_available()
            if(flag != 0):
                volume_id = self.read_volume_id()
            else:
                if(image_id != ""):
                    volume = self.volumes_client.create_volume(
                        size=size,
                        volume_type=volume_type_id,
                        imageRef=image_id,
                        availability_zone=az_name)
                else:
                    volume = self.volumes_client.create_volume(
                        size=size,
                        expected_resp=self.expected_resp,
                        volume_type=volume_type_id,
                        availability_zone=az_name)
                volume_id = volume['volume']['id']
                waiters.wait_for_volume_resource_status(self.volumes_client,
                                               volume_id, 'available')
        else:
            if(image_id != ""):
                volume = self.volumes_client.create_volume(
                    size=size,
                    volume_type=volume_type_id,
                    imageRef=image_id,
                    availability_zone=az_name)
            else:
                volume = self.volumes_client.create_volume(
                    size=size, volume_type=volume_type_id, availability_zone=az_name)
            volume_id = volume['volume']['id']
            waiters.wait_for_volume_resource_status(self.volumes_client,
                                           volume_id, 'available')
        if(tvaultconf.cleanup and volume_cleanup):
            self.addCleanup(self.delete_volume, volume_id)
        return volume_id

    '''
    Method deletes a given volume
    '''

    def delete_volume(self, volume_id):
        try:
            volume_snapshots = self.get_volume_snapshots(volume_id)
            LOG.debug("Volumes snapshots for: " +
                      str(volume_id) + ": " + str(volume_snapshots))
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
            self.snapshots_extensions_client.delete_snapshot(
                volume_snapshot_id)
            LOG.debug('Snapshot delete operation completed %s' %
                      volume_snapshot_id)
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
                LOG.debug('Snapshot delete operation completed %s' %
                          volume_snapshots[snapshot])
            except Exception as e:
                LOG.error("Exception: " + str(e))

    '''
    Method to return list of available volume snapshots
    '''

    def get_available_volume_snapshots(self):
        volume_snapshots = []
        resp = self.snapshots_extensions_client.list_snapshots(detail=True)
        for id in range(0, len(resp['snapshots'])):
            volume_snapshots.append(resp['snapshots'][id]['id'])
        LOG.debug("Volume snapshots: " + str(volume_snapshots))
        return volume_snapshots

    '''
    Method to return list of available volume snapshots for given volume
    '''

    def get_volume_snapshots(self, volume_id):
        volume_snapshots = []
        resp = self.snapshots_extensions_client.list_snapshots(detail=True)
        for id in range(0, len(resp['snapshots'])):
            volume_snapshot_id = resp['snapshots'][id]['volumeId']
            if (volume_id == volume_snapshot_id):
                volume_snapshots.append(resp['snapshots'][id]['id'])
        LOG.debug("Volume snapshots: " + str(volume_snapshots))
        return volume_snapshots

    '''
    Method returns the list of attached volumes to a given VM instance
    '''

    def get_attached_volumes(self, server_id):
        server = self.servers_client.show_server(server_id)['server']
        volumes = server['os-extended-volumes:volumes_attached']
        volume_list = []
        for volume in volumes:
            volume_list.append(volume['id'])
        LOG.debug("Attached volumes: " + str(volume_list))
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

    def attach_volume(
        self,
        volume_id,
        server_id,
        device="/dev/vdb",
        attach_cleanup=True):
        if(not tvaultconf.workloads_from_file):
            if(tvaultconf.volumes_from_file):
                try:
                    LOG.debug("attach_volume: volumeId: %s, serverId: %s" %
                              (volume_id, server_id))
                    self.servers_client.attach_volume(
                        server_id, volumeId=volume_id, device=device)
                    waiters.wait_for_volume_resource_status(self.volumes_client,
                                               volume_id, 'in-use')
                except Exception as e:
                    pass
            else:
                LOG.debug("attach_volume: volumeId: %s, serverId: %s" %
                          (volume_id, server_id))
                self.servers_client.attach_volume(
                    server_id, volumeId=volume_id, device=device)
                waiters.wait_for_volume_resource_status(self.volumes_client,
                                               volume_id, 'in-use')
        if(tvaultconf.cleanup and attach_cleanup):
            self.addCleanup(self.detach_volume, server_id, volume_id)

    '''
    Method to detach given volume from given VM instance
    '''

    def detach_volume(self, server_id, volume_id):
        try:
            body = self.volumes_client.show_volume(volume_id)['volume']
            self.volumes_client.detach_volume(volume_id)
            waiters.wait_for_volume_resource_status(self.volumes_client,
                                               volume_id, 'available')
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
            waiters.wait_for_volume_resource_status(self.volumes_client,
                                           volumes[volume], 'available')

    '''
    Method creates a workload and returns Workload id
    '''

    def workload_create(
        self,
        instances,
        workload_type,
        jobschedule={},
        workload_name="",
        workload_cleanup=True,
        description='test'):
        if(tvaultconf.workloads_from_file):
            flag = 0
            flag = self.is_workload_available()
            if(flag != 0):
                workload_id = self.read_workload_id()
            else:
                in_list = []
                ts = str(datetime.now())
                workload_name = "tempest" + ts.replace('.', '-')
                for id in instances:
                    in_list.append({'instance-id': id})
                payload = {'workload': {'name': workload_name,
                                        'workload_type_id': workload_type,
                                        'source_platform': 'openstack',
                                        'instances': in_list,
                                        'jobschedule': jobschedule,
                                        'metadata': {},
                                        'description': description}}
                resp, body = self.wlm_client.client.post(
                    "/workloads", json=payload)
                workload_id = body['workload']['id']
                LOG.debug(
                    "#### workloadid: %s , operation:workload_create" %
                    workload_id)
                LOG.debug("Response:" + str(resp.content))
                if(resp.status_code != 202):
                    resp.raise_for_status()
        else:
            in_list = []
            if(workload_name == ""):
                ts = str(datetime.now())
                workload_name = "tempest" + ts.replace('.', '-')
            for id in instances:
                in_list.append({'instance-id': id})
            payload = {'workload': {'name': workload_name,
                                    'workload_type_id': workload_type,
                                    'source_platform': 'openstack',
                                    'instances': in_list,
                                    'jobschedule': jobschedule,
                                    'metadata': {},
                                    'description': description}}
            resp, body = self.wlm_client.client.post(
                "/workloads", json=payload)
            workload_id = body['workload']['id']
            LOG.debug("#### workloadid: %s , operation:workload_create" %
                      workload_id)
            time.sleep(30)
            while (self.getWorkloadStatus(workload_id) !=
                   "available" and self.getWorkloadStatus(workload_id) != "error"):
                LOG.debug('workload status is: %s , sleeping for 30 sec' %
                          self.getWorkloadStatus(workload_id))
                time.sleep(30)

            LOG.debug("Response:" + str(resp.content))
            if(resp.status_code != 202):
                resp.raise_for_status()
        LOG.debug('WorkloadCreated: %s' % workload_id)
        if(tvaultconf.cleanup and workload_cleanup):
            self.addCleanup(self.workload_delete, workload_id)
        return workload_id

    '''
    Method deletes a given workload
    '''

    def workload_delete(self, workload_id):
        try:
            # Delete snapshot
            snapshot_list_of_workload = self.getSnapshotList(workload_id)

            if len(snapshot_list_of_workload) > 0:
                for i in range(0, len(snapshot_list_of_workload)):
                    self.snapshot_delete(
                        workload_id, snapshot_list_of_workload[i])

            resp, body = self.wlm_client.client.delete(
                "/workloads/" + workload_id)
            LOG.debug(
                "#### workloadid: %s , operation: workload_delete" %
                workload_id)
            LOG.debug("Response:" + str(resp.content))
            LOG.debug('WorkloadDeleted: %s' % workload_id)
            return True
        except Exception as e:
            return False

    '''
    Method creates oneclick snapshot for a given workload and returns snapshot id
    '''

    def workload_snapshot(
        self,
        workload_id,
        is_full,
        snapshot_name="",
        snapshot_cleanup=True):
        if (snapshot_name == ""):
            snapshot_name = 'Tempest-test-snapshot'
        LOG.debug("Snapshot Name: " + str(snapshot_name))
        payload = {'snapshot': {'name': snapshot_name,
                                'description': 'Test',
                                'full': 'True'}}
        LOG.debug("Snapshot Payload: " + str(payload))
        self.wait_for_workload_tobe_available(workload_id)
        if(is_full):
            resp, body = self.wlm_client.client.post(
                "/workloads/" + workload_id + "?full=1", json=payload)
        else:
            resp, body = self.wlm_client.client.post(
                "/workloads/" + workload_id, json=payload)
        snapshot_id = body['snapshot']['id']
        LOG.debug(
            "#### workload_id: %s ,snapshot_id: %s , operation: workload_snapshot" %
            (workload_id, snapshot_id))
        LOG.debug("Snapshot Response:" + str(resp.content))
        # self.wait_for_workload_tobe_available(workload_id)
        if(tvaultconf.cleanup and snapshot_cleanup):
            self.addCleanup(self.snapshot_delete, workload_id, snapshot_id)
        return snapshot_id

    '''
    Method resets the given workload
    '''

    def workload_reset(self, workload_id):
        self.wait_for_workload_tobe_available(workload_id)
        resp, body = self.wlm_client.client.post(
            "/workloads/" + workload_id + "/reset")
        LOG.debug("#### workloadid: %s, operation: workload-reset " %
                  workload_id)
        LOG.debug("Response:" + str(resp.content))
        LOG.debug("Response code:" + str(resp.status_code))
        if (resp.status_code != 202):
            resp.raise_for_status()

    '''
    Method to do workload reassign
    '''

    def workload_reassign(self, new_tenant_id, workload_ids, user_id):
        try:
            payload = [{"workload_ids": [workload_ids],
                        "migrate_cloud": False,
                        "old_tenant_ids": [],
                        "user_id": user_id,
                        "new_tenant_id":new_tenant_id}]
            resp, body = self.wlm_client.client.post(
                "/workloads/reasign_workloads", json=payload)
            reassignstatus = body['workloads']['reassigned_workloads'][0]['status']
            LOG.debug("Response:" + str(resp.content))
            if(resp.status_code != 200):
                resp.raise_for_status()
            else:
                if reassignstatus == "available":
                    return(0)
        except Exception as e:
            LOG.debug("Exception: " + str(e))

    '''
    Method to wait until the workload is available
    '''

    def wait_for_workload_tobe_available(self, workload_id):
        status = "available"
        start_time = int(time.time())
        LOG.debug('Checking workload status')
        while (status != self.getWorkloadStatus(workload_id)):
            if (self.getWorkloadStatus(workload_id) == 'error'):
                LOG.debug('workload status is: %s , workload create failed' %
                          self.getWorkloadStatus(workload_id))
                #raise Exception("Workload creation failed")
                return False
            LOG.debug('workload status is: %s , sleeping for 30 sec' %
                      self.getWorkloadStatus(workload_id))
            time.sleep(30)
        LOG.debug('workload status of workload %s: %s' %
                  (workload_id, self.getWorkloadStatus(workload_id)))
        return True

    '''
    Method to check if snapshot is successful
    '''

    def is_snapshot_successful(self, workload_id, snapshot_id):
        is_successful = "False"
        if(self.getSnapshotStatus(workload_id, snapshot_id) == 'available'):
            LOG.debug('snapshot successful: %s' % snapshot_id)
            is_successful = "True"
        return is_successful

    '''
    Method deletes a given snapshot
    '''

    def snapshot_delete(self, workload_id, snapshot_id):
        LOG.debug("Deleting snapshot {}".format(snapshot_id))
        resp, body = self.wlm_client.client.delete(
            "/snapshots/" + str(snapshot_id))
        LOG.debug(
            "#### workloadid: %s ,snapshot_id: %s  , Operation: snapshot_delete" %
            (workload_id, snapshot_id))
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 202):
            resp.raise_for_status()
        self.wait_for_workload_tobe_available(workload_id)
        LOG.debug('SnapshotDeleted: %s' % snapshot_id)
        return True

    '''
    Method creates one click restore for a given snapshot and returns the restore id
    '''

    def snapshot_restore(
        self,
        workload_id,
        snapshot_id,
        restore_name="",
        restore_cleanup=True):
        LOG.debug("At the start of snapshot_restore method")
        if(restore_name == ""):
            restore_name = tvaultconf.snapshot_restore_name
        payload = {
            "restore": {
                "options": {
                    "description": "Tempest test restore",
                    "vmware": {},
                    "openstack": {
                        "instances": [],
                        "zone": ""},
                    "restore_type": "oneclick",
                    "type": "openstack",
                    "oneclickrestore": "True",
                    "restore_options": {},
                    "name": restore_name},
                "name": restore_name,
                "description": "Tempest test restore"}}
        LOG.debug(
            "In snapshot_restore method, before calling waitforsnapshot method")
        self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
        LOG.debug("After returning from wait for snapshot")
        resp, body = self.wlm_client.client.post(
            "/workloads/" + workload_id + "/snapshots/" + snapshot_id + "/restores", json=payload)
        restore_id = body['restore']['id']
        LOG.debug(
            "#### workloadid: %s ,snapshot_id: %s , restore_id: %s , operation: snapshot_restore" %
            (workload_id, snapshot_id, restore_id))
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 202):
            resp.raise_for_status()
        LOG.debug('Restore of snapshot %s scheduled succesffuly' % snapshot_id)
        self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
        self.restored_vms = self.get_restored_vm_list(restore_id)
        self.restored_volumes = self.get_restored_volume_list(restore_id)
        if(tvaultconf.cleanup and restore_cleanup):
            #self.restored_vms = self.get_restored_vm_list(restore_id)
            #self.restored_volumes = self.get_restored_volume_list(restore_id)
            self.addCleanup(self.restore_delete, workload_id,
                            snapshot_id, restore_id)
            self.addCleanup(self.delete_restored_vms,
                            self.restored_vms, self.restored_volumes)
        return restore_id

    '''
    Method creates selective restore for a given snapshot and returns the restore id
    '''

    def snapshot_selective_restore(
        self,
        workload_id,
        snapshot_id,
        restore_name="",
        restore_desc="",
        instance_details=[],
        network_details=[],
        network_restore_flag=False,
        restore_cleanup=True,
        sec_group_cleanup=False):
        LOG.debug("At the start of snapshot_selective_restore method")
        if(restore_name == ""):
            restore_name = "Tempest_test_restore"
        if(restore_desc == ""):
            restore_desc = "Tempest_test_restore_description"
        if len(instance_details) > 0:
            payload = {
                "restore": {
                    "options": {
                        'name': restore_name,
                        'description': restore_desc,
                        'type': 'openstack',
                                'oneclickrestore': False,
                        'restore_type': 'selective',
                        'openstack': {
                            'instances': instance_details,
                            'restore_topology': network_restore_flag,
                            'networks_mapping': {'networks': network_details}
                            }
                        }
                    }
                }
            #self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            resp, body = self.wlm_client.client.post(
                "/workloads/" + workload_id + "/snapshots/" + snapshot_id + "/restores", json=payload)
            restore_id = body['restore']['id']
            LOG.debug(
                "#### workloadid: %s ,snapshot_id: %s , restore_id: %s , operation: snapshot_restore" %
                (workload_id, snapshot_id, restore_id))
            LOG.debug("Response:" + str(resp.content))
            if(resp.status_code != 202):
                resp.raise_for_status()
            LOG.debug('Restore of snapshot %s scheduled succesffuly' %
                      snapshot_id)
            if(tvaultconf.cleanup and restore_cleanup):
                self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
                self.restored_vms = self.get_restored_vm_list(restore_id)
                self.restored_volumes = self.get_restored_volume_list(
                    restore_id)
                self.addCleanup(self.restore_delete,
                                workload_id, snapshot_id, restore_id)
                if sec_group_cleanup:
                    self.restored_security_group_id = self.get_security_group_id_by_name(
                        "snap_of_" + tvaultconf.security_group_name)
                    self.addCleanup(self.delete_security_group,
                                    self.restored_security_group_id)
                self.addCleanup(self.delete_restored_vms,
                                self.restored_vms, self.restored_volumes)
        else:
            restore_id = 0
        return restore_id

    '''
    Method returns the list of restored VMs
    '''

    def get_restored_vm_list(self, restore_id):
        resp, body = self.wlm_client.client.get("/restores/" + str(restore_id))
        LOG.debug("Body: " + str(body))
        LOG.debug("Response: " + str(resp))
        instances = body['restore']['instances']
        restore_vms = []
        for instance in instances:
            LOG.debug("instance:" + instance['id'])
            restore_vms.append(instance['id'])
        LOG.debug("Restored vms list:" + str(restore_vms))
        return restore_vms

    '''
    Method returns the list of restored volumes
    '''

    def get_restored_volume_list(self, restore_id):
        resp, body = self.wlm_client.client.get("/restores/" + restore_id)
        LOG.debug("Body: " + str(body))
        LOG.debug("Response: " + str(resp))
        instances = body['restore']['instances']
        restored_volumes = []
        for instance in instances:
            LOG.debug("instance:" + instance['id'])
            if len(self.get_attached_volumes(instance['id'])) > 0:
                for volume in self.get_attached_volumes(instance['id']):
                    restored_volumes.append(volume)
        LOG.debug("restored volume list:" + str(restored_volumes))
        return restored_volumes

    '''
    Method deletes the given restored VMs and volumes
    '''

    def delete_restored_vms(self, restored_vms, restored_volumes):
        LOG.debug("Deletion of retored vms {} started.".format(restored_vms))
        self.delete_vms(restored_vms)
        LOG.debug("Deletion of restored volumes {} started.".format(
            restored_volumes))
        self.delete_volumes(restored_volumes)

    '''
    Method to wait until the snapshot is available
    '''

    def wait_for_snapshot_tobe_available(self, workload_id, snapshot_id):
        status = "available"
        LOG.debug('Checking snapshot status')
        while (status != self.getSnapshotStatus(workload_id, snapshot_id)):
            if(self.getSnapshotStatus(workload_id, snapshot_id) == 'error'):
                LOG.debug('Snapshot status is: %s' %
                          self.getSnapshotStatus(workload_id, snapshot_id))
                raise Exception("Snapshot creation failed")
            LOG.debug('Snapshot status is: %s' %
                      self.getSnapshotStatus(workload_id, snapshot_id))
            time.sleep(10)
        LOG.debug('Final Status of snapshot: %s' %
                  (self.getSnapshotStatus(workload_id, snapshot_id)))
        return status

    '''
    Method to check if restore is successful
    '''

    def is_restore_successful(self, workload_id, snapshot_id, restore_id):
        is_successful = "False"
        if(self.getRestoreStatus(workload_id, snapshot_id, restore_id) == 'available'):
            is_successful = "True"
        return is_successful

    '''
    Method returns if scheduler is running for a given workload
    '''

    def is_schedule_running(self, workload_id):
        is_running = False
        snapshot_list = self.getSnapshotList(workload_id)
        for i in range(0, (len(snapshot_list))):
            FMT = "%Y-%m-%dT%H:%M:%S.000000"
            snapshot_info = []
            snapshot_info = self.getSnapshotInfo(snapshot_list[i])
            SnapshotCreateTime = snapshot_info[0]
            LOG.debug('snapshot create time is: %s' % SnapshotCreateTime)
            SnapshotNameInfo = snapshot_info[1]
            if (i == 0):
                if(SnapshotNameInfo == 'jobscheduler'):
                    is_running = True
                    LOG.debug('snapshot is running: %s' % snapshot_list[i])
                    self.wait_for_workload_tobe_available(workload_id)
                else:
                    LOG.debug('snapshot is not running: %s' % snapshot_list[i])
                    is_running = False
            else:
                previous_snapshot_info = self.getSnapshotInfo(
                    snapshot_list[i - 1])
                SnapshotCreateTime1 = previous_snapshot_info[0]
                tdelta = datetime.strptime(
                    SnapshotCreateTime, FMT) - datetime.strptime(SnapshotCreateTime1, FMT)
                LOG.debug('Time Interval Between Two snapshot is: %s' %
                          str(tdelta))
                if(SnapshotNameInfo == 'jobscheduler' and (str(tdelta) == "1:00:00")):
                    is_running = True
                    LOG.debug('snapshot is running: %s' % str(tdelta))
                    self.wait_for_workload_tobe_available(workload_id)
                else:
                    LOG.debug('snapshot is not running: %s' % snapshot_list[i])
                    is_running = False
        return is_running

    '''
    Method to delete a given restore
    '''

    def restore_delete(self, workload_id, snapshot_id, restore_id):
        LOG.debug("Deletion of restore {0} of snapshot {1} started".format(
            restore_id, snapshot_id))
        self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
        resp, body = self.wlm_client.client.delete(
            "/workloads/" + workload_id + "/snapshots/" + snapshot_id + "/restores/" + restore_id)
        LOG.debug(
            "#### workloadid: %s ,snapshot_id: %s  , Operation: restore_delete" %
            (workload_id, snapshot_id))
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 202):
            resp.raise_for_status()
        self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
        LOG.debug('RestoreDeleted: %s' % workload_id)

    '''
    Method to check if VM details are available in file
    '''

    def is_vm_available(self):
        dir = os.path.dirname(os.path.abspath(__file__))
        filename = dir + "/vms_file"
        LOG.debug("vms_file_path:%s" % filename)
        with open(filename) as f:
            content = f.read().splitlines()
            if not content:
                return False
            else:
                LOG.debug("vm_from_file: %s" % content[0])
                return True

    '''
    Method to return the VM id from file
    '''

    def read_vm_id(self):
        dir = os.path.dirname(os.path.abspath(__file__))
        filename = dir + "/vms_file"
        LOG.debug("vms_file_path:%s" % filename)
        with open(filename, "r+") as f:
            vms = f.read().splitlines()
            vm_id = vms[0]
            f.seek(0)
            for vm in vms:
                if vm != vm_id:
                    f.write(vm)
            f.truncate()
            return vm_id

    '''
    Method to check if volume details are available in file
    '''

    def is_volume_available(self):
        dir = os.path.dirname(os.path.abspath(__file__))
        filename = dir + "/volumes_file"
        LOG.debug("volumes_file_path:%s" % filename)
        with open(filename) as f:
            content = f.read().splitlines()
            if not content:
                return False
            else:
                LOG.debug("volume_from_file: %s" % content[0])
                return True

    '''
    Method to return the volume id from file
    '''

    def read_volume_id(self):
        dir = os.path.dirname(os.path.abspath(__file__))
        filename = dir + "/volumes_file"
        LOG.debug("volumes_file_path:%s" % filename)
        with open(filename, "r+") as f:
            volumes = f.read().splitlines()
            volume_id = volumes[0]
            f.seek(0)
            for volume in volumes:
                if volume != volume_id:
                    f.write(volume)
            f.truncate()
            return volume_id

    '''
    Method to check if workload details are available in file
    '''

    def is_workload_available(self):
        dir = os.path.dirname(os.path.abspath(__file__))
        filename = dir + "/workloads_file"
        LOG.debug("workloads_file_path:%s" % filename)
        with open(filename) as f:
            content = f.read().splitlines()
            if not content:
                return False
            else:
                LOG.debug("workload_from_file: %s" % content[0])
                return True

    '''
    Method to return the workload id from file
    '''

    def read_workload_id(self):
        dir = os.path.dirname(os.path.abspath(__file__))
        filename = dir + "/workloads_file"
        LOG.debug("workloads_file_path:%s" % filename)
        with open(filename, "r+") as f:
            workloads = f.read().splitlines()
            workload_id = workloads[0]
            f.seek(0)
            for workload in workloads:
                if workload != workload_id:
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
            f.write('Snapshot is running : ' + str(date) + '\n')
        else:
            date = time.strftime("%c")
            f.write('Snapshot Not running : ' + str(date) + '\n')
            tvaultconf.sched.remove_job('my_job_id')
            tvaultconf.sched.shutdown(wait=False)
        if (tvaultconf.count == tvaultconf.No_of_Backup):
            tvaultconf.sched.remove_job('my_job_id')
            tvaultconf.sched.shutdown(wait=False)

    '''
    Method to fetch the list of network ports
    '''

    def get_port_list(self):
        port_list = self.ports_client.list_ports()
        LOG.debug("Port List: " + str(port_list))
        return port_list

    '''
    Method to delete list of ports
    '''

    def delete_ports(self, port_list):
        for i in range(0, len(port_list)):
            port_delete = self.ports_client.delete_port(port_list[i])
            LOG.debug("Port %s status %s" % (port_list[i], port_delete))

    '''
    Method returns the snapshot list information
    '''

    def getSnapshotList(self, workload_id=None):
        if(workload_id is not None):
            resp, body = self.wlm_client.client.get(
                "/snapshots?workload_id=" + workload_id)
        else:
            resp, body = self.wlm_client.client.get("/snapshots")
        snapshot_list = []
        for i in range(0, len(body['snapshots'])):
            snapshot_list.append(body['snapshots'][i]['id'])
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return snapshot_list

    '''
    Method returns the snapshot information . It return array with create time,name and type information for given snapshot
    '''

    def getSnapshotInfo(self, snapshot_id='none'):
        resp, body = self.wlm_client.client.get("/snapshots/" + snapshot_id)
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
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return snapshot_info

    '''
    Method to connect to remote linux machine
    '''

    def SshRemoteMachineConnection(self, ipAddress, userName, password):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # ssh.load_system_host_keys()
        ssh.connect(hostname=ipAddress, username=userName, password=password)
        return ssh

    '''
    Method to list all floating ips
    '''

    def get_floating_ips(self):
        floating_ips_list = []
        get_ips_response = self.floating_ips_client.list_floatingips()
        LOG.debug("get floating ips response: " + str(get_ips_response))
        floating_ips = get_ips_response['floatingips']
        for ip in floating_ips:
            LOG.debug("portid: " + str(ip['port_id']))
            if str(
                ip['port_id']) == "None" or str(
                ip['port_id']) == "":
                floating_ips_list.append(ip['floating_ip_address'])
        LOG.debug('floating_ips' + str(floating_ips_list))
        return floating_ips_list

    '''
    Method to associate floating ip to a server
    '''

    def set_floating_ip(
        self,
        floating_ip,
        server_id,
        floatingip_cleanup=False):
        port_details = self.ports_client.list_ports(device_id=server_id)['ports']
        floating_ip_id = self.floating_ips_client.list_floatingips(
            floating_ip_address=floating_ip)['floatingips']
        set_response = self.floating_ips_client.update_floatingip(
            floating_ip_id[0]['id'], port_id=port_details[0]['id'])
        # self.SshRemoteMachineConnectionWithRSAKey(floating_ip)
        if(tvaultconf.cleanup and floatingip_cleanup):
            self.addCleanup(
                self.disassociate_floating_ip_from_server,
                floating_ip,
                server_id)
        return set_response

    '''
    Method to create SSH connection using RSA Private key
    '''

    def SshRemoteMachineConnectionWithRSAKey(
        self, ipAddress, username=tvaultconf.instance_username):
        key_file = str(tvaultconf.key_pair_name) + ".pem"
        ssh = paramiko.SSHClient()
        private_key = paramiko.RSAKey.from_private_key_file(key_file)
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # ssh.load_system_host_keys()
        flag = False
        for i in range(0, 30, 1):
            LOG.debug("Trying to connect to " + str(ipAddress))
            if(flag):
                break
            try:
                ssh.connect(hostname=ipAddress, username=username,
                            pkey=private_key, timeout=20)
                flag = True
            except Exception as e:
                time.sleep(20)
                if i == 29:
                    raise
                LOG.debug("Got into Exception.." + str(e))
            else:
                break
        return ssh

    '''
    Method to create SSH connection using RSA Private key and its name
    '''

    def SshRemoteMachineConnectionWithRSAKeyName(
        self, ipAddress, key_name, username=tvaultconf.instance_username):
        key_file = key_name + ".pem"
        ssh = paramiko.SSHClient()
        private_key = paramiko.RSAKey.from_private_key_file(key_file)
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.load_system_host_keys()
        flag = False
        for i in range(0, 30, 1):
            LOG.debug("Trying to connect to " + str(ipAddress))
            if(flag):
                break
            try:
                ssh.connect(hostname=ipAddress, username=username,
                            pkey=private_key, timeout=20)
                flag = True
            except Exception as e:
                time.sleep(20)
                if i == 29:
                    raise
                LOG.debug("Got into Exception.." + str(e))
            else:
                break
        return ssh

    '''
    layout creation and formatting the disks
    '''

    def execute_command_disk_create(
        self,
        ssh,
        ipAddress,
        volumes,
        mount_points):
        self.channel = ssh.invoke_shell()
        commands = []
        for volume in volumes:
            commands.extend(["sudo fdisk {}".format(volume),
                             "n",
                             "p",
                             "1",
                             "2048",
                             "2097151",
                             "w",
                             "yes | sudo mkfs -t ext3 {}1".format(volume)])

        for command in commands:
            LOG.debug("Executing: " + str(command))
            self.channel.send(command + "\n")
            time.sleep(5)
            while not self.channel.recv_ready():
                time.sleep(3)

            output = self.channel.recv(9999)
            LOG.debug(str(output))

    '''
    disks mounting
    '''

    def execute_command_disk_mount(
        self,
        ssh,
        ipAddress,
        volumes,
        mount_points):
        LOG.debug("Execute command disk mount connecting to " + str(ipAddress))

        self.channel = ssh.invoke_shell()
        for i in range(len(volumes)):

            commands = [
                "sudo mkdir " +
                mount_points[i],
                "sudo mount {0}1 {1}".format(
                    volumes[i],
                    mount_points[i]),
                "sudo df -h"]

            for command in commands:
                LOG.debug("Executing: " + str(command))
                self.channel.send(command + "\n")
                time.sleep(3)
                while not self.channel.recv_ready():
                    time.sleep(2)

                output = self.channel.recv(9999)
                LOG.debug(str(output))
                time.sleep(2)
    '''
    add custom sied files on linux
    '''

    def addCustomSizedfilesOnLinux(self, ssh, dirPath, fileCount):
        try:
            LOG.debug("build command data population : " +
                      str(dirPath) + "number of files: " + str(fileCount))
            for count in range(fileCount):
                buildCommand = "sudo openssl rand -out " + \
                    str(dirPath) + "/" + "File" + "_" + \
                    str(count + 1) + ".txt -base64 $(( 2**25 * 3/4 ))"
                stdin, stdout, stderr = ssh.exec_command(buildCommand)
                time.sleep(20)
        except Exception as e:
            LOG.debug("Exception: " + str(e))

    '''
    add custom sied files on linux using dd command
    '''

    def addCustomfilesOnLinuxVM(self, ssh, dirPath, fileCount):
        try:
            LOG.debug("build command data population : " +
                      str(dirPath) + " number of files : " + str(fileCount))
            for count in range(fileCount):
                buildCommand = "sudo dd if=/dev/urandom of=" + \
                    str(dirPath) + "/" + "File_" + \
                    str(count + 1) + " bs=2M count=10"
                LOG.debug("Executing command -> " + buildCommand)
                stdin, stdout, stderr = ssh.exec_command(buildCommand)
                time.sleep(9 * fileCount)
        except Exception as e:
            LOG.debug("Exception : " + str(e))
    '''
    calculate md5 checksum
    '''

    def calculatemmd5checksum(self, ssh, dirPath):
        local_md5sum = ""
        buildCommand = "sudo find " + \
            str(dirPath) + "/ -type f -exec md5sum {} +"
        LOG.debug("build command for md5 checksum calculation" +
                  str(buildCommand))
        stdin, stdout, stderr = ssh.exec_command(buildCommand)
        time.sleep(15)
        output = stdout.readlines()
        LOG.debug("command executed: " + str(output))
        for line in output:
            local_md5sum += str(line.split(" ")[0])
        return local_md5sum

    '''
    Method returns the list of details of restored VMs
    '''

    def get_vm_details(self, server_id):
        response = self.servers_client.show_server(server_id)
        LOG.debug("Vm details :" + str(response))
        return response

    '''
    Method to populate data before full backup
    '''

    def data_populate_before_backup(
        self,
        workload_instances,
        floating_ips_list,
        backup_size,
        files_count,
        mount_points):
        md5sums_dir_before = {}
        for id in range(len(workload_instances)):
            self.md5sums = ""
            LOG.debug("setting floating ip" +
                      (floating_ips_list[id].encode('ascii', 'ignore')))
            for mount_point in mount_points:
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                    floating_ips_list[id])
                self.addCustomSizedfilesOnLinux(
                    ssh, mount_point + "/", files_count)
                ssh.close()
            for mount_point in mount_points:
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                    floating_ips_list[id])
                self.md5sums += (self.calculatemmd5checksum(ssh, mount_point))
                ssh.close()
            md5sums_dir_before[str(floating_ips_list[id])] = self.md5sums
            LOG.debug("before backup md5sum for " +
                      floating_ips_list[id].encode('ascii', 'ignore') +
                      " " +
                      str(self.md5sums))

        LOG.debug("before backup md5sum : " + str(md5sums_dir_before))
        return md5sums_dir_before

    '''
    Method to populate data before full backup
    '''

    def calculate_md5_after_restore(
        self,
        workload_instances,
        floating_ips_list,
        volumes,
        mount_points):
        LOG.debug("Calculating md5 sums for :" +
                  str(workload_instances) + "||||" + str(floating_ips_list))
        md5sums_dir_after = {}
        for id in range(len(workload_instances)):
            self.md5sums = ""
            # md5sums_dir_after = {}
            ssh = self.SshRemoteMachineConnectionWithRSAKey(
                floating_ips_list[id])
            self.execute_command_disk_mount(
                ssh, floating_ips_list[id], volumes, mount_points)
            ssh.close()
            for mount_point in mount_points:
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                    floating_ips_list[id])
                self.md5sums += (self.calculatemmd5checksum(ssh, mount_point))
                ssh.close()
            md5sums_dir_after[str(floating_ips_list[id])] = self.md5sums

            LOG.debug("after md5sum for " + floating_ips_list[id].encode(
                'ascii', 'ignore') + " " + str(self.md5sums))

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

        keypair_response = self.keypairs_client.create_keypair(
            name=keypair_name)
        privatekey = keypair_response['keypair']['private_key']
        fingerprint = keypair_response['keypair']['fingerprint']
        with open(str(keypair_name) + ".pem", 'w+') as f:
            f.write(str(privatekey))
        os.chmod(str(keypair_name) + ".pem", stat.S_IRWXU)
        LOG.debug("keypair fingerprint : " + str(fingerprint))
        if(tvaultconf.cleanup and keypair_cleanup):
            self.addCleanup(self.delete_key_pair, keypair_name)
        return fingerprint

    '''
    Method to disassociate floating ip to a server
    '''

    def disassociate_floating_ip_from_server(self, floating_ip, server_id):
        LOG.debug("Disassociation of " + str(floating_ip) +
                  " from " + str(server_id) + " started.")
        set_response = self.servers_client.action(
            server_id, "removeFloatingIp", address=str(floating_ip))
        return set_response

    '''
    Method to fetch id of given floating ip
    '''

    def get_floatingip_id(self, floating_ip):
        floatingip_id = None
        floatingips = self.floating_ips_client.list_floatingips()
        for i in range(len(floatingips['floatingips'])):
            if(str(floatingips['floatingips'][i]['floating_ip_address']) == str(floating_ip)):
                floatingip_id = floatingips['floatingips'][i]['id']
                LOG.debug("floating ip id for :" +
                          str(floating_ip) + " is: " + str(floatingip_id))
        return floatingip_id

    '''
    Method to fetch port id of given floating ip
    '''

    def get_portid_of_floatingip(self, floating_ip):
        port_id = None
        floatingips = self.floating_ips_client.list_floatingips()
        for i in range(len(floatingips['floatingips'])):
            if(str(floatingips['floatingips'][i]['floating_ip_address']) == str(floating_ip)):
                port_id = floatingips['floatingips'][i]['port_id']
                LOG.debug("port id for :" + str(floating_ip) +
                          " is: " + str(port_id))
        return port_id

    '''
    Method to get key pair details
    '''

    def get_key_pair_details(self, keypair_name):
        foorprint = ""
        key_pairs_list_response = self.keypairs_client.show_keypair(
            keypair_name)
        fingerprint = key_pairs_list_response['keypair']['fingerprint']
        LOG.debug("keypair fingerprint : " + str(fingerprint))
        return fingerprint

    '''Fetch required details of the instances'''

    def get_vms_details_list(self, vm_details_list):
        self.vms_details = []
        for i in range(len(vm_details_list)):
            server_id = vm_details_list[i]['server']['id']
            if len(vm_details_list[i]['server']['addresses'][list(
                vm_details_list[i]['server']['addresses'].keys())[0]]) == 2:
                floatingip = str(vm_details_list[i]['server']['addresses'][list(
                    vm_details_list[i]['server']['addresses'].keys())[0]][1]['addr'])
            else:
                floatingip = None
            if "security_groups" not in list(
                vm_details_list[i]['server'].keys()):
                security_group = None
            else:
                security_group = vm_details_list[i]['server']['security_groups']

            tmp_json = {
                'id': server_id,
                'name': vm_details_list[i]['server']['name'],
                'network_name': list(
                    vm_details_list[i]['server']['addresses'].keys())[0],
                'keypair': vm_details_list[i]['server']['key_name'],
                'floating_ip': floatingip,
                'vm_status': vm_details_list[i]['server']['status'],
                'vm_power_status': vm_details_list[i]['server']['OS-EXT-STS:vm_state'],
                'availability_zone': vm_details_list[i]['server']['OS-EXT-AZ:availability_zone'],
                'flavor_id': vm_details_list[i]['server']['flavor']['id'],
                'security_groups': security_group}
            self.vms_details.append(tmp_json)
        return self.vms_details

    '''floating ip availability'''

    def get_floating_ip_status(self, ip):
        floating_ip_status = self.floating_ips_client.show_floatingip(ip)
        LOG.debug("floating ip details fetched: " + str(floating_ip_status))

    '''get network name  by id'''

    def get_net_name(self, network_id):
        try:
            net_name = list(self.networks_client.show_network(
                network_id).items())[0][1]['name']
            return net_name
        except TypeError as te:
            LOG.debug("TypeError: " + str(te))
            net_name = list(self.networks_client.show_network(
                network_id).items())[0][1][0]['name']
            return net_name
        except Exception as e:
            LOG.error("Exception in get_net_name: " + str(e))
            return None

    '''get subnet id'''

    def get_subnet_id(self, network_id):
        subnet_list = list(self.subnets_client.list_subnets().items())[0][1]
        for subnet in subnet_list:
            if subnet['network_id'] == network_id:
                return subnet['id']

    '''delete key'''

    def delete_key_pair(self, keypair_name):
        LOG.debug("Deleting key pair {}".format(keypair_name))
        key_pairs_list_response = self.keypairs_client.list_keypairs()
        key_pairs = key_pairs_list_response['keypairs']
        for key in key_pairs:
            if str(key['keypair']['name']) == keypair_name:
                self.keypairs_client.delete_keypair(keypair_name)

    '''delete security group'''

    def delete_security_group(self, security_group_id):
        try:
            self.security_groups_client.delete_security_group(
                security_group_id)
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
        internal_network_name = str((list(self.get_vm_details(
            server_id)['server']['addresses'].keys())[0]))
        fixed_ip = str((self.get_vm_details(server_id)[
                       'server']['addresses'][internal_network_name][0]['addr']))
        ports.append(self.get_port_id(fixed_ip))
        LOG.debug("Port deletion for " + str(ports) + " started.")
        self.delete_ports(ports)

    '''create_security_group'''

    def create_security_group(self, name, description, secgrp_cleanup=True):
        self.security_group_id = self.security_groups_client.create_security_group(
            name=name, description=description)['security_group']['id']
        if(tvaultconf.cleanup and secgrp_cleanup):
            self.addCleanup(self.delete_security_group, self.security_group_id)
        return self.security_group_id

    '''get_security_group_details'''

    def get_security_group_details(self, security_group_id):
        security_group_details = (
            self.security_groups_client.show_security_group(
                str(security_group_id)))
        LOG.debug(security_group_details)
        return security_group_details

    '''get_security_group_id_by_name'''

    def get_security_group_id_by_name(self, security_group_name):
        security_group_id = ""
        security_groups_list = self.security_groups_client.list_security_groups()[
            'security_groups']
        LOG.debug("Security groups list" + str(security_groups_list))
        for security_group in security_groups_list:
            if security_group['name'] == security_group_name:
                security_group_id = security_group['id']
        if security_group_id != "":
            return security_group_id
        else:
            return None

    '''create_flavor'''

    def create_flavor(
        self,
        name=CONF.compute.flavor_name,
        disk=CONF.compute.flavor_disk,
        vcpus=CONF.compute.flavor_vcpus,
        ram=CONF.compute.flavor_ram,
        swap=0,
        ephemeral=0,
        flavor_cleanup=True):
        if(ephemeral == 0):
            flavor_id = self.flavors_client.create_flavor(
                name=name, disk=disk, vcpus=vcpus, ram=ram, swap=swap)['flavor']['id']
            LOG.debug("flavor id" + str(flavor_id))
        else:
            flavor_id = self.flavors_client.create_flavor(
                name=name,
                disk=disk,
                vcpus=vcpus,
                ram=ram,
                swap=swap,
                ephemeral=ephemeral)['flavor']['id']
        if(tvaultconf.cleanup and flavor_cleanup):
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
        flavor_details = {
            'ram': flavor_resp['ram'],
            'OS-FLV-DISABLED:disabled': flavor_resp['OS-FLV-DISABLED:disabled'],
            'vcpus': flavor_resp['vcpus'],
            'swap': flavor_resp['swap'],
            'os-flavor-access:is_public': flavor_resp['os-flavor-access:is_public'],
            'rxtx_factor': flavor_resp['rxtx_factor'],
            'OS-FLV-EXT-DATA:ephemeral': flavor_resp['OS-FLV-EXT-DATA:ephemeral'],
            'disk': flavor_resp['disk']}
        return flavor_details

    '''Set a volume as bootable'''

    def set_volume_as_bootable(self, volume_id, bootable=True):
        vol_resp = self.volumes_client.set_bootable_volume(volume_id, bootable=True)
        LOG.debug("Volume bootable response: " + str(vol_resp))
        return vol_resp

    '''Get list of workloads available'''

    def getWorkloadList(self):
        resp, body = self.wlm_client.client.get("/workloads")
        workload_list = []
        for i in range(0, len(body['workloads'])):
            workload_list.append(body['workloads'][i]['id'])
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return workload_list

    '''
    Method to fetch global job scheduler status
    '''

    def get_global_job_scheduler_status(self):
        resp, body = self.wlm_client.client.get("/global_job_scheduler")
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        status = body['global_job_scheduler']
        return status

    '''
    Method to enable global job scheduler
    '''

    def enable_global_job_scheduler(self):
        resp, body = self.wlm_client.client.post(
            "/global_job_scheduler/enable")
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        status = body['global_job_scheduler']
        return status

    '''
    Method to disable global job scheduler
    '''

    def disable_global_job_scheduler(self):
        resp, body = self.wlm_client.client.post(
            "/global_job_scheduler/disable")
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        status = body['global_job_scheduler']
        return status

    '''
    Method to create triliovault license
    '''

    def create_license(self, filename, key):
        flag = True
        msg = ""
        payload = {"license": {"file_name": filename, "lic_txt": key}}
        try:
            resp, body = self.wlm_client.client.post(
                "/workloads/license", json=payload)
            LOG.debug("Response:" + str(resp.content))
        except Exception as e:
            LOG.error("Exception: " + str(e))
            flag = False
            msg = str(e)
        finally:
            LOG.debug("flag: " + str(flag) + " msg: " + str(msg))
            if(flag):
                return flag
            else:
                return msg

    '''
    Method to fetch license list
    '''

    def get_license_list(self):
        resp, body = self.wlm_client.client.get("/workloads/metrics/license")
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        data = body['license']
        return data

    '''
    Method returns the schedule details of a given workload
    '''

    def getSchedulerDetails(self, workload_id):
        resp, body = self.wlm_client.client.get("/workloads/" + workload_id)
        schedule_details = body['workload']['jobschedule']
        LOG.debug("#### workloadid: %s , operation:show_workload" %
                  workload_id)
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return schedule_details

    '''
    Method returns snapshot details
    '''

    def getSnapshotDetails(self, workload_id, snapshot_id):
        resp, body = self.wlm_client.client.get(
            "/workloads/" + workload_id + "/snapshots/" + snapshot_id)
        snapshot_details = body['snapshot']
        LOG.debug(
            "#### workloadid: %s ,snapshot_id: %s , operation:show_snapshot" %
            (workload_id, snapshot_id))
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return snapshot_details

    '''
    Method to get license check
    '''

    def get_license_check(self):
        flag = True
        msg = ""
        try:
            resp, body = self.wlm_client.client.get(
                "/workloads/metrics/license_check")
            LOG.debug("Response:" + str(resp.content))
            msg = body['message']
        except Exception as e:
            LOG.error("Exception: " + str(e))
            flag = False
            msg = str(e)
        finally:
            LOG.debug("flag: " + str(flag) + " msg: " + str(msg))
            return msg

    '''
    Method runs file search and returns filesearch id for given instance id and path
    '''

    def filepath_search(
        self,
        vm_id,
        path,
        snapshot_ids=[],
        start=0,
        end=0,
        date_from="",
        date_to=""):
        payload = {"file_search": {"end": end,
                                   "filepath": path,
                                   "date_from": date_from,
                                   "snapshot_ids": snapshot_ids,
                                   "start": start,
                                   "date_to": date_to,
                                   "vm_id": vm_id}}

        resp, body = self.wlm_client.client.post("/search", json=payload)
        filesearch_id = body['file_search']['id']
        LOG.debug("#### filesearchid: %s , operation:filepath_search" %
                  filesearch_id)
        time.sleep(30)
        while (self.getSearchStatus(filesearch_id) !=
               "completed" and self.getSearchStatus(filesearch_id) != "error"):
            LOG.debug('filepath_search status is: %s , sleeping for 30 sec' %
                      self.getSearchStatus(filesearch_id))
            time.sleep(30)
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 202):
            resp.raise_for_status()
        return filesearch_id

    '''
    Method returns the current status of file search for given filesearch id
    '''

    def getSearchStatus(self, filesearch_id):
        resp, body = self.wlm_client.client.get(
            "/search/" + str(filesearch_id))
        filesearch_status = body['file_search']['status']
        LOG.debug(
            "#### filesearchid: %s , filesearch status: %s, operation: filepath_search_status" %
            (filesearch_id, filesearch_status))
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return filesearch_status

    '''
    Method returns snapshot wise file count for given filesearch id and path
    '''

    def verifyFilepath_Search(self, filesearch_id, path):
        resp, body = self.wlm_client.client.get(
            "/search/" + str(filesearch_id))
        LOG.debug("Response:" + str(resp.content))
        resp = json.loads(resp.content)
        snapshot_wise_filecount = {}
        path1 = ""
        if "*" in path:
            path1 = path.strip("*")
        elif "?" in path:
            path1 = path.split("?")[0]
        else:
            path1 = path
        for k, v in list(resp["file_search"].items()):
            if k == "json_resp":
                data = eval(v)
                for k1 in range(len(data)):
                    for k2, v2 in list(data[k1].items()):
                        for k3 in data[k1][k2]:
                            if "*" in path or "?" in path:
                                i = 0
                                for k4, v4 in list(k3.items()):
                                    if len(v4) != 0 and "/dev" in k4:
                                        for k5 in v4:
                                            disk = list(k3.keys())[0]
                                            if path1 in k5:
                                                i += 1
                                            else:
                                                break
                                    disk = list(k3.keys())[0]
                                if i != 0 and k2 not in list(
                                    snapshot_wise_filecount.keys()):
                                    LOG.debug("File exist in " +
                                              k2 + " in volume " + disk)
                                    snapshot_wise_filecount[k2] = i
                                elif i != 0 and k2 in list(snapshot_wise_filecount.keys()):
                                    LOG.debug("File exist in " +
                                              k2 + " in volume " + disk)
                                    snapshot_wise_filecount[k2] = snapshot_wise_filecount[k2] + i
                                elif k2 not in list(snapshot_wise_filecount.keys()):
                                    LOG.debug("File not exist in " +
                                              k2 + " in volume " + disk)
                                    snapshot_wise_filecount[k2] = i
                                elif k2 in list(snapshot_wise_filecount.keys()):
                                    pass
                            else:
                                i = 0
                                for k4, v2 in list(k3.items()):
                                    if path1 in k4:
                                        disk = list(k3.keys())[1]
                                        i += 1
                                    else:
                                        break
                                if i != 0:
                                    LOG.debug("File exist in " +
                                              k2 + " in volume " + disk)
                                    snapshot_wise_filecount[k2] = i
                                elif i != 0 and k2 in list(snapshot_wise_filecount.keys()):
                                    LOG.debug("File exist in " +
                                              k2 + " in volume " + disk)
                                    snapshot_wise_filecount[k2] = snapshot_wise_filecount[k2] + i
                                elif k2 not in list(snapshot_wise_filecount.keys()):
                                    snapshot_wise_filecount[k2] = i
                                elif k2 in list(snapshot_wise_filecount.keys()):
                                    pass
                        LOG.debug("Total Files found = " +
                                  str(snapshot_wise_filecount[k2]))
                LOG.debug(
                    "Total number of files found in each snapshot =" +
                    str(snapshot_wise_filecount))
        return snapshot_wise_filecount

    '''
    Method to mount snapshot and return the status
    '''

    def mount_snapshot(
        self,
        workload_id,
        snapshot_id,
        vm_id,
        mount_cleanup=True):
        is_successful = True
        payload = {"mount": {"mount_vm_id": vm_id,
                             "options": {}}}
        resp, body = self.wlm_client.client.post(
            "/snapshots/" + snapshot_id + "/mount", json=payload)
        LOG.debug("#### Mounting of snapshot is initiated: ")
        if(resp.status_code != 200):
            resp.raise_for_status()
        LOG.debug("Getting snapshot mount status")
        while(self.getSnapshotStatus(workload_id, snapshot_id) != "mounted"):
            if(self.getSnapshotStatus(workload_id, snapshot_id) == "available"):
                LOG.debug('Snapshot status is: %s' %
                          self.getSnapshotStatus(workload_id, snapshot_id))
                is_successful = False
                return is_successful
            LOG.debug('snapshot mount status is: %s , sleeping for 30 sec' %
                      self.getSnapshotStatus(workload_id, snapshot_id))
            time.sleep(30)
        if(tvaultconf.cleanup and mount_cleanup):
            self.addCleanup(self.unmount_snapshot, workload_id, snapshot_id)
        return is_successful

    '''
    Method to unmount snapshot and return the status
    '''

    def unmount_snapshot(self, workload_id, snapshot_id):
        try:
            resp, body = self.wlm_client.client.post(
                "/snapshots/" + snapshot_id + "/dismount")
            LOG.debug(
                "#### snapshotid: %s , operation: unmount_snapshot" %
                snapshot_id)
            LOG.debug("Response status code:" + str(resp.status_code))
            LOG.debug('Snapshot unmounted: %s' % snapshot_id)
            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            LOG.debug('Snapshot status is: %s' %
                      self.getSnapshotStatus(workload_id, snapshot_id))
            return True
        except Exception as e:
            LOG.debug('Snapshot unmount failed: %s' % snapshot_id)
            return False

    '''
    Method to add newadmin role and newadmin_api rule to "workload:get_storage_usage" operation and "workload:get_nodes" operations in policy.json file on tvault
    Method to add backup role and backup_api rule to "snapshot_create", "snapshot_delete", "workload_create", "workload_delete", "restore_create" and  "restore_delete" operation
    and "workload:get_nodes" operations in policy.json file on tvault
    '''

    def change_policyjson_file(self, role, rule, policy_changes_cleanup=True):
        for ip in tvaultconf.tvault_ip:
            ssh = self.SshRemoteMachineConnection(ip, tvaultconf.tvault_dbusername,
                        tvaultconf.tvault_password)
            if role == "newadmin":
                old_rule = "admin_api"
                LOG.debug("Add %s role in policy.json", role)
                operations = ["workload:get_storage_usage", "workload:get_nodes"]

            elif role == "backup":
                old_rule = "admin_or_owner"
                LOG.debug("Add %s role in policy.json", role)
                operations = ["workload:workload_snapshot", "snapshot:snapshot_delete", "workload:workload_create",
                              "workload:workload_delete", "snapshot:snapshot_restore", "restore:restore_delete"]

            role_add_command = 'sed -i \'2s/^/\\t"{0}":[["role:{1}"]],\\n/\' /etc/workloadmgr/policy.json'.format(
                    rule, role)
            rule_assign_command = ""
            for op in operations:
                rule_assign_command += '; ' + 'sed -i \'s/"{2}": "rule:{1}"/"{2}": "rule:{0}"/g\'  \
                                 /etc/workloadmgr/policy.json'.format(rule, old_rule, op)
            LOG.debug("role_add_command: %s ;\n rule_assign_command: %s", role_add_command, rule_assign_command)
            commands = role_add_command + rule_assign_command
            LOG.debug("Commands to add role: %s", commands)
            stdin, stdout, stderr = ssh.exec_command(commands)
            if(tvaultconf.cleanup and policy_changes_cleanup):
                self.addCleanup(self.revert_changes_policyjson, old_rule)
            ssh.close()

    '''
    Method to revert changes of role and rule in policy.json file on tvault
    Method to delete newadmin role and newadmin_api rule was assigned to "workload:get_storage_usage" operation and "workload:get_nodes" operations in policy.json file on tvault
    Method to delete backup role and backup_api rule was assigned to "snapshot_create", "snapshot_delete", "workload_create", "workload_delete", "restore_create" and  "restore_delete" operation
    and "workload:get_nodes" operations in policy.json file on tvault
    '''

    def revert_changes_policyjson(self, rule):
        for ip in tvaultconf.tvault_ip:
            ssh = self.SshRemoteMachineConnection(ip, tvaultconf.tvault_dbusername,
                        tvaultconf.tvault_password)
            if rule == "admin_api":
                role = "newadmin_api"
                operations = ["workload:get_storage_usage", "workload:get_nodes"]

            elif rule == "admin_or_owner":
                role = "backup_api"
                operations = ["workload:workload_snapshot", "snapshot:snapshot_delete", "workload:workload_create", 
                              "workload:workload_delete", "snapshot:snapshot_restore", "restore:restore_delete"]

            role_delete_command = "sed -i '/{0}\":/d' /etc/workloadmgr/policy.json".format(role)
            rule_reassign_command = ""
            for op in operations:
                rule_reassign_command += '; ' + 'sed -i \'s/"{2}": "rule:{1}"/"{2}": "rule:{0}"/g\' /etc/workloadmgr/policy.json'.format(rule, role, op)
            LOG.debug("role_delete_command: %s ;\n rule_reassign_command: %s", role_delete_command, rule_reassign_command)
            commands = role_delete_command + rule_reassign_command
            LOG.debug("Commands to revert policy changes: %s", commands)
            stdin, stdout, stderr = ssh.exec_command(commands)
            ssh.close()

    '''
    add security group rule
    '''

    def add_security_group_rule(
        self,
        parent_grp_id="",
        remote_grp_id="",
        ip_proto="",
        from_prt=1,
        to_prt=40000):
        LOG.debug("parent group id: {}".format(str(parent_grp_id)))
        LOG.debug("remote_group_id: {}".format(str(remote_grp_id)))
        if remote_grp_id != "":
            self.security_group_rules_client.create_security_group_rule(
                security_group_id=parent_grp_id,
                remote_group_id=remote_grp_id,
                protocol=ip_proto,
                port_range_min=from_prt,
                port_range_max=to_prt,
                direction="ingress")
            self.security_group_rules_client.create_security_group_rule(
                security_group_id=parent_grp_id,
                remote_group_id=remote_grp_id,
                protocol=ip_proto,
                port_range_min=from_prt,
                port_range_max=to_prt,
                direction="egress")
        else:
            self.security_group_rules_client.create_security_group_rule(
                security_group_id=parent_grp_id,
                protocol=ip_proto,
                port_range_min=from_prt,
                port_range_max=to_prt,
                direction="ingress")
            self.security_group_rules_client.create_security_group_rule(
                security_group_id=parent_grp_id,
                protocol=ip_proto,
                port_range_min=from_prt,
                port_range_max=to_prt,
                direction="egress")


    '''
    delete some files on linux
    '''

    def deleteSomefilesOnLinux(self, ssh, mount_point, number):
        self.channel = ssh.invoke_shell()
        command = "sudo rm -rf {}/File_1.txt"
        LOG.debug("Executing: " + str(command))
        self.channel.send(command + "\n")
        while not self.channel.recv_ready():
            time.sleep(3)

        output = self.channel.recv(9999)
        LOG.debug(str(output))

    '''
    Method to fetch details of a specific workload
    '''

    def get_workload_details(self, workload_id):
        resp, body = self.wlm_client.client.get("/workloads/" + workload_id)
        workload_data = body['workload']
        LOG.debug("#### workloadid: %s , operation:show_workload" %
                  workload_id)
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return workload_data

    '''
    Method to update trilioVault email settings
    '''

    def update_email_setings(
        self,
        setting_data,
        project_id=CONF.identity.admin_tenant_id,
        category="",
        is_public=False,
        is_hidden=False,
        metadata={},
        type="",
        description=""):
        settings = []
        for k, v in list(setting_data.items()):
            data = {"name": str(k),
                    "category": category,
                    "is_public": is_public,
                    "is_hidden": is_hidden,
                    "metadata": metadata,
                    "type": type,
                    "description": description,
                    "value": str(v)}
            settings.append(data)
        payload_data = {"settings": settings}
        LOG.debug("Payload_data: " + str(payload_data))
        resp, body = self.wlm_client.client.post(
            "/settings", json=payload_data)
        setting_data = body['settings']
        LOG.debug("Update email Setting Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return setting_data

    '''
    Method to fetch trilioVault email settings
    '''

    def get_settings_list(self):
        resp, body = self.wlm_client.client.post("/workloads/settings")
        setting_list = body['settings']
        LOG.debug("List Setting Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return setting_list

    '''
    Method to update user email in openstack
    '''

    def update_user_email(
        self,
        user_id,
        email_id,
        project_id=CONF.identity.tenant_id):
        try:
            if CONF.identity_feature_enabled.api_v2:
                resp = self.identity_client.update_user(
                    user_id, email=email_id)
            else:
                resp = self.identity_client.update_user(
                    user_id, email=email_id, default_project_id=project_id)
            return True
        except Exception as e:
            LOG.error("Exception in update_user(): %s" % str(e))
            return False

    '''
    Method to fetch trilioVault email settings
    '''

    def delete_setting(self, setting_name):
        resp, body = self.wlm_client.client.delete(
            "/settings/" + str(setting_name))
        if(resp.status_code != 200):
            # resp.raise_for_status()
            return False
        return True

    '''
    Method returns the restore list information
    '''

    def getRestoreList(self, snapshot_id=None):
        if(snapshot_id is not None):
            resp, body = self.wlm_client.client.get(
                "/restores?snapshot_id=" + snapshot_id)
        else:
            resp, body = self.wlm_client.client.get("/restores")
        restore_list = []
        for i in range(0, len(body['restores'])):
            restore_list.append(body['restores'][i]['id'])
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return restore_list

    '''
    Method returns restore details
    '''

    def getRestoreDetails(self, restore_id):
        resp, body = self.wlm_client.client.get("/restores/" + restore_id)
        restore_details = body['restore']
        LOG.debug("#### restoreid: %s , operation:show_restore" % (restore_id))
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return restore_details

    '''
    Method to get tenant chargeback API
    '''

    def getTenantChargeback(self):
        try:
            resp, body = self.wlm_client.client.get(
                "/workloads/metrics/tenants_chargeback")
            LOG.debug("Chargeback API Response:" + str(resp.content))
            LOG.debug("Chargeback API Body:" + str(body))
            if(resp.status_code != 200):
                resp.raise_for_status()
            return body
        except Exception as e:
            LOG.debug("Exception: " + str(e))
            return False

    '''
    Method to get vm protected API
    '''

    def getVMProtected(self):
        try:
            resp, body = self.wlm_client.client.get(
                "/workloads/metrics/vms_protected")
            LOG.debug("Get Protected VM Response:" + str(resp.content))
            LOG.debug("Get Protected VM Body:" + str(body))
            if(resp.status_code != 200):
                resp.raise_for_status()
            return body
        except Exception as e:
            LOG.debug("Exception: " + str(e))
            return False

    '''
    Method to get tenant usage API
    '''

    def getTenantUsage(self):
        try:
            resp, body = self.wlm_client.client.get(
                "/workloads/metrics/tenants_usage")
            LOG.debug("Get Tenant Usage Response:" + str(resp.content))
            LOG.debug("Get Tenant Usage Body:" + str(body))
            if(resp.status_code != 200):
                resp.raise_for_status()
            return body
        except Exception as e:
            LOG.debug("Exception: " + str(e))
            return False

    '''
    This method creats a workload policy and return policy_id
    '''

    def workload_policy_create(
        self,
        policy_name=tvaultconf.policy_name,
        fullbackup_interval=tvaultconf.fullbackup_interval,
        interval=tvaultconf.interval,
        retention_policy_value=tvaultconf.retention_policy_value,
        retention_policy_type=tvaultconf.retention_policy_type,
        description='description',
        policy_cleanup=True):
        payload = {"workload_policy": {
            "field_values": {
                "fullbackup_interval": fullbackup_interval,
                "retention_policy_type": retention_policy_type,
                "interval": interval,
                "retention_policy_value": retention_policy_value
                },
            "display_name": policy_name,
            "display_description": description,
            "metadata": {}
            }
            }
        resp, body = self.wlm_client.client.post(
            "/workload_policy/", json=payload)
        policy_id = body['policy']['id']
        LOG.debug(
            "#### policyid: %s , operation:workload_policy_create" % policy_id)
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 202):
            resp.raise_for_status()

        LOG.debug('PolicyCreated: %s' % policy_id)
        if(tvaultconf.cleanup and policy_cleanup):
            self.addCleanup(self.workload_policy_delete, policy_id)
        return policy_id

    '''
    This method updates workload policy and return status
    '''

    def workload_policy_update(
        self,
        policy_id,
        policy_name='policy_update',
        fullbackup_interval=tvaultconf.fullbackup_interval,
        interval=tvaultconf.interval,
        retention_policy_value=tvaultconf.retention_policy_value,
        retention_policy_type=tvaultconf.retention_policy_type,
        description='description'):
        try:
            payload = {
                "policy": {
                    "field_values": {
                        "fullbackup_interval": fullbackup_interval,
                        "retention_policy_type": retention_policy_type,
                        "interval": interval,
                        "retention_policy_value": retention_policy_value},
                    "display_name": policy_name,
                    "display_description": description}}
            resp, body = self.wlm_client.client.put(
                "/workload_policy/" + policy_id, json=payload)
            LOG.debug("Response:" + str(resp.content))
            if(resp.status_code != 202):
                resp.raise_for_status()
            LOG.debug('PolicyUpdated: %s' % policy_id)
            return True
        except Exception as e:
            LOG.debug('Policyupdate failed: %s' % policy_id)
            return False

    '''
    This method deletes workload policy and return status
    '''

    def workload_policy_delete(self, policy_id):
        try:
            details = self.get_policy_details(policy_id)
            list_of_project_assigned_to_policy = details[4]
            for i in range(len(list_of_project_assigned_to_policy)):
                self.assign_unassign_workload_policy(
                    policy_id, remove_project_ids_list=list_of_project_assigned_to_policy[i])

            resp, body = self.wlm_client.client.delete(
                "/workload_policy/" + policy_id)
            LOG.debug(
                "#### policy id: %s , operation: workload_policy_delete" %
                policy_id)
            LOG.debug("Response:" + str(resp.content))
            if(resp.status_code != 202):
                resp.raise_for_status()
            LOG.debug('WorkloadPolicyDeleted: %s' % policy_id)
            return True
        except Exception as e:
            LOG.debug("Exception: " + str(e))
            return False

    '''
    This method assign/unassign workload policy to tenants
    '''

    def assign_unassign_workload_policy(
        self,
        policy_id,
        add_project_ids_list=[],
        remove_project_ids_list=[]):
        try:
            payload = {"policy":
                       {
                           "remove_projects": remove_project_ids_list,
                           "add_projects": add_project_ids_list
                           }
                       }
            resp, body = self.wlm_client.client.post(
                "/workload_policy/" + policy_id + "/assign", json=payload)
            policy_id = body['policy']['id']
            LOG.debug(
                "#### policyid: %s , operation:assignorunassign_workload_policy" %
                policy_id)
            LOG.debug("Response:" + str(resp.content))
            if(resp.status_code != 202):
                resp.raise_for_status()
            return True
        except Exception as e:
            LOG.debug("Exception: " + str(e))
            return False

    '''
    Method to get policy details
    #return name, {retention_policy_type, interval, retention_policy_value, fullbackup_interval}, [list_of_project_assigned], id and description in one list
    '''

    def get_policy_details(self, policy_id):
        try:
            resp, body = self.wlm_client.client.get(
                "/workload_policy/" + policy_id)
            LOG.debug("Response:" + str(resp.content))
            if(resp.status_code != 202):
                resp.raise_for_status()
            list_of_project_assigned = []
            policy_name = body['policy']['name']
            field_values = {}
            for i in range(len(body['policy']['field_values'])):
                key = body['policy']['field_values'][i]['policy_field_name']
                value = body['policy']['field_values'][i]['value']
                field_values[key] = value
            policy_id = body['policy']['id']
            description = body['policy']['description']
            for i in range(len(body['policy']['policy_assignments'])):
                list_of_projects_assigned1 = body['policy']['policy_assignments'][i]['project_id']
                list_of_project_assigned.append(list_of_projects_assigned1)
            return [
                policy_name,
                field_values,
                policy_id,
                description,
                list_of_project_assigned]
        except Exception as e:
            LOG.debug("Exception: " + str(e))
            return False

    '''
    Method to return policy-list, returns id's
    '''

    def get_policy_list(self):
        try:
            resp, body = self.wlm_client.client.get("/workload_policy/")
            LOG.debug("Response:" + str(resp.content))
            if(resp.status_code != 202):
                resp.raise_for_status()
            policy_list = []
            for i in range(len(body['policy_list'])):
                policy_id = body['policy_list'][i]['id']
                policy_list.append(policy_id)
            return policy_list
        except Exception as e:
            LOG.debug("Exception: " + str(e))
            return False

    '''
    Method returns mountpoint path of backup target media
    '''

    def get_mountpoint_path(self, ipaddress, username, password):
        ssh = self.SshRemoteMachineConnection(ipaddress, username, password)
        show_mountpoint_cmd = "mount | grep triliovault-mounts | awk '{print $3}'"
        stdin, stdout, stderr = ssh.exec_command(show_mountpoint_cmd)
        mountpoint_path = stdout.read()
        LOG.debug("mountpoint path is : " + str(mountpoint_path))
        print(mountpoint_path)
        ssh.close()
        return mountpoint_path

    '''
    Method returns True if snapshot dir is exists on backup target media
    '''

    def check_snapshot_exist_on_backend(
        self,
        ipaddress,
        username,
        password,
        mount_path,
        workload_id,
        snapshot_id):
        ssh = self.SshRemoteMachineConnection(ipaddress, username, password)
        snapshot_path = str(mount_path).strip() + "/workload_" + \
            str(workload_id).strip() + "/snapshot_" + str(snapshot_id).strip()
        is_snapshot_exist = "test -d " + \
            str(snapshot_path).strip() + \
            " && echo 'exists' ||echo 'not exists'"
        LOG.debug("snapshot command is : " + str(is_snapshot_exist))
        stdin, stdout, stderr = ssh.exec_command(is_snapshot_exist)
        snapshot_exists = stdout.read()
        LOG.debug("is snapshot exists command output" + str(snapshot_exists))
        if str(snapshot_exists) == 'exists':
            return True
        elif str(snapshot_exists).strip() == 'not exists':
            return False

    '''
    Method to return policies list assigned to particular project
    '''

    def assigned_policies(self, project_id):
        try:
            resp, body = self.wlm_client.client.get(
                "/workload_policy/assigned/" + project_id)
            LOG.debug("Response:" + str(resp.content))
            if(resp.status_code != 202):
                resp.raise_for_status()
            project_list_assigned_policies = []
            for i in range(len(body['policies'])):
                policy_id = body['policies'][i]['policy_id']
                project_list_assigned_policies.append(policy_id)
            return project_list_assigned_policies
        except Exception as e:
            LOG.debug("Exception: " + str(e))
            return False

    '''
    Method to return details of given workload
    '''

    def getWorkloadDetails(self, workload_id):
        resp, body = self.wlm_client.client.get("/workloads/" + workload_id)
        workload_data = body['workload']
        LOG.debug("#### workloadid: %s , operation:show_workload" %
                  workload_id)
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return workload_data

    '''
    Method to fetch trust list
    '''

    def get_trust_list(self):
        resp, body = self.wlm_client.client.get("/trusts")
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        data = body['trust']
        return data

    '''
    Method to restart wlm-api service on tvault
    '''

    def restart_wlm_api_service(self):
        for ip in tvaultconf.tvault_ip:
            ssh = self.SshRemoteMachineConnection(ip, tvaultconf.tvault_dbusername,
                        tvaultconf.tvault_password)
        command = "service wlm-api restart"
        stdin, stdout, stderr = ssh.exec_command(command)
        time.sleep(3)
        command = "service wlm-api status | grep 'Active'"
        stdin, stdout, stderr = ssh.exec_command(command)
        status_update = stdout.read()
        ssh.close()
        return status_update

    '''
    connet to fvm , validate that snapshot is mounted on fvm
    '''

    def validate_snapshot_mount(
        self,
        ssh,
        file_path_to_search="/mnt/tvault-mounts/mounts/",
        file_name="File_1"):
        try:
            time.sleep(20)
            cmd = "sudo su - root -c 'ls -la " + file_path_to_search + "/Test_*/vda*'"
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
            LOG.debug("In VDA List files output: %s ; list files error: %s", stdout.read(), stderr.read())
            cmd = "sudo su - root -c 'ls -la " + file_path_to_search + "/Test_*/vdb*'"
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
            LOG.debug("In VDB List files output: %s ; list files error: %s", stdout.read(), stderr.read())
            buildCommand = "sudo su - root -c 'find "  + file_path_to_search + " -name " + file_name + "'"
            LOG.debug("build command to search file is :" + str(buildCommand))
            stdin, stdout, stderr = ssh.exec_command(buildCommand, timeout=120)
            output = stdout.read()
            LOG.debug(output)
            return(bytes(output))
        except Exception as e:
            LOG.debug("Exception: " + str(e))

    '''
    Method to fetch the list of network ports by network_id
    '''

    def get_port_list_by_network_id(self, network_id):
        port_list = self.ports_client.list_ports(network_id=network_id)
        capture_port_list = []
        for details in port_list['ports']:
            capture_port_list.append(details['id'])
        LOG.debug("Port List by network_id: " + str(capture_port_list))
        return capture_port_list

    '''
    Method to fetch the list of router ids
    '''

    def get_router_ids(self):
        router_list = self.routers_client.list_routers()
        capture_router_list = []
        for details in router_list['routers']:
            capture_router_list.append(details['id'])
        LOG.debug("router ids: " + str(capture_router_list))
        return capture_router_list

    '''
    Delete routers
    '''

    def delete_routers(self, router_list):
        for router_id in router_list:
            self.routers_client.delete_router(router_id)
        LOG.debug("delete router")

    '''
    Delete Router routes
    '''

    def delete_router_routes(self, router_list):
        for router in router_list:
            if router['routes'] != []:
                self.routers_client.update_router(
                    router['id'], **{'routes': []})
        LOG.debug("Deleted routes of routers")

    '''
    Method to delete list of ports
    '''

    def delete_network(self, network_id):
        ports_list = []
        router_id_list = []
        routers = self.routers_client.list_routers()['routers']
        routers = [x for x in routers if x['tenant_id'] ==
                   CONF.identity.tenant_id]
        self.delete_router_routes(routers)
        router_id_list = [x['id']
                          for x in routers if x['tenant_id'] == CONF.identity.tenant_id]
        for router in router_id_list:
            self.delete_router_interfaces(router)
        self.delete_routers(router_id_list)
        ports_list = self.get_port_list_by_network_id(network_id)
        self.delete_ports(ports_list)
        network_delete = self.networks_client.delete_network(network_id)

    '''
    Method to delete router interface
    '''

    def delete_router_interfaces(self, router_id):
        interfaces = self.ports_client.list_ports(device_owner='network:router_interface')['ports']
        for interface in interfaces:
            for i in interface['fixed_ips']:
                self.routers_client.remove_router_interface(
                                    interface['device_id'], subnet_id=i['subnet_id'])

    '''
    Method returns the auditlog information
    '''

    def getAuditLog(self, time_in_minutes="1440"):
        resp, body = self.wlm_client.client.get(
            "/workloads/audit/auditlog?time_in_minutes=" + time_in_minutes)
        LOG.debug("Audit Log Response: " + str(resp))
        LOG.debug("Audit Log Content:" + str(body))
        audit_log_list = []
        audit_log_list = body['auditlog']
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return audit_log_list

    '''
    Method returns the storage usage information
    '''

    def getStorageUsage(self):
        resp, body = self.wlm_client.client.get(
            "/workloads/metrics/storage_usage")
        LOG.debug("Storage Usage Response:" + str(resp))
        LOG.debug("Storage Usage Content :" + str(body))
        storage_usage_list = []
        storage_usage_list = body['storage_usage']
        LOG.debug("Response:" + str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return storage_usage_list

    '''
    Method to delete entire network topology
    This method won't delete public network
    '''

    def delete_network_topology(self):
        LOG.debug("Deleting the existing networks")
        networkslist = self.networks_client.list_networks()['networks']

        for network in networkslist:
            if network['router:external'] == False and network['tenant_id'] == CONF.identity.tenant_id:
                self.delete_network(network['id'])
            else:
                pass

    '''
    Method to create network topology for network restore
    Here specific network topology will be created in order to test the possible scenarios for network restore
    '''

    def create_network(self):
        routers = {}
        subnets = {}
        nets = {}
        for x in range(1, 7):
            if x != 7:
                net = self.networks_client.create_network(
                    **{'name': "Private-{}".format(x)})
                nets[net['network']['name']] = net['network']['id']
                subnetconfig = {
                    'ip_version': 4,
                    'network_id': net['network']['id'],
                    'name': "PS-{}".format(x),
                    'gateway_ip': '10.10.{}.1'.format(x),
                    'cidr': '10.10.{}.0/24'.format(x)}
                subnet = self.subnets_client.create_subnet(**subnetconfig)
                subnets[subnet['subnet']['name']] = subnet['subnet']['id']
            else:
                net = self.networks_client.create_network(
                    **{'name': "Private-{}".format(x), 'admin_state_up': 'False', 'shared': 'True'})
                nets[net['network']['name']] = net['network']['id']

        for x in range(1, 6):
            if x != 3:
                router = self.routers_client.create_router(
                    **{'name': "Router-{}".format(x)})
            else:
                router = self.routers_client.create_router(
                    **{'name': "Router-{}".format(x), 'admin_state_up': 'False'})
            routers[router['router']['name']] = router['router']['id']

        networkslist = self.networks_client.list_networks()['networks']
        self.routers_client.add_router_interface(routers['Router-1'], subnet_id=subnets['PS-1'])
        self.routers_client.add_router_interface(routers['Router-1'], subnet_id=subnets['PS-2'])
        self.routers_client.add_router_interface(routers['Router-3'], subnet_id=subnets['PS-3'])
        self.routers_client.add_router_interface(routers['Router-2'], subnet_id=subnets['PS-4'])
        portid1 = self.ports_client.create_port(
            **{'network_id': nets['Private-2'], 'fixed_ips': [{'ip_address': '10.10.2.4'}]})['port']['id']
        self.routers_client.add_router_interface(routers['Router-2'], port_id=portid1)
        portid2 = self.ports_client.create_port(
            **{'network_id': nets['Private-2'], 'fixed_ips': [{'ip_address': '10.10.2.5'}]})['port']['id']
        portid3 = self.ports_client.create_port(
            **{'network_id': nets['Private-2'], 'fixed_ips': [{'ip_address': '10.10.2.6'}]})['port']['id']
        self.routers_client.add_router_interface(routers['Router-4'], port_id=portid2)
        self.routers_client.add_router_interface(routers['Router-5'], port_id=portid3)
        self.routers_client.add_router_interface(routers['Router-4'], subnet_id=subnets['PS-5'])
        portid4 = self.ports_client.create_port(
            **{'network_id': nets['Private-5'], 'fixed_ips': [{'ip_address': '10.10.5.3'}]})['port']['id']
        self.routers_client.add_router_interface(routers['Router-5'], port_id=portid4)

        for router_name, router_id in list(routers.items()):
            if router_name == 'Router-1':
                self.routers_client.update_router(
                    router_id, **{'routes': [{'destination': '10.10.5.0/24', 'nexthop': '10.10.2.6'}]})
            elif router_name in ['Router-4', 'Router-5']:
                self.routers_client.update_router(
                    router_id, **{'routes': [{'destination': '10.10.1.0/24', 'nexthop': '10.10.2.1'}]})

        return networkslist

    '''
    Get network topology details
    Here only specific values which are fixed are extracted out because for network topology comparison we can't compare values which are dynamic for ex. ids, created_at, updated_at etc.
    '''

    def get_topology_details(self):
        networkslist = self.networks_client.list_networks()['networks']
        nws = [x['id'] for x in networkslist]
        nt = [{str(i): str(j) for i,
               j in list(x.items()) if i not in ('network_id',
                                                 'subnets',
                                                 'created_at',
                                                 'updated_at',
                                                 'id',
                                                 'revision_number',
                                                 'provider:segmentation_id')} for x in networkslist]
        networks = {}
        for each_network in nt:
            networks[each_network['name']] = each_network

        sbnt = self.subnets_client.list_subnets()['subnets']
        sbnts = [{str(i): str(j) for i, j in list(x.items()) if i not in (
            'network_id', 'created_at', 'updated_at', 'id', 'revision_number')} for x in sbnt]
        subnets = {}
        for each_subnet in sbnts:
            subnets[each_subnet['name']] = each_subnet

        rs = self.routers_client.list_routers()['routers']
        rts = [{str(i): str(j) for i,
                j in list(x.items()) if i not in ('external_gateway_info',
                                                  'created_at',
                                                  'updated_at',
                                                  'id',
                                                  'revision_number')} for x in rs]
        routers = {}
        for each_router in rts:
            routers[each_router['name']] = each_router

        interfaces = {}
        for router in self.get_router_ids():
            interfaceslist = self.ports_client.list_ports()['ports']
            intrfs = [{str(i): str(j) for i,
                       j in list(x.items()) if i not in ('network_id',
                                                         'created_at',
                                                         'updated_at',
                                                         'mac_address',
                                                         'fixed_ips',
                                                         'id',
                                                         'device_id',
                                                         'security_groups',
                                                         'port_security_enabled',
                                                         'revision_number')} for x in interfaceslist]
            interfaces[self.routers_client.show_router(
                router)['router']['name']] = intrfs
        return(networks, subnets, routers, interfaces)

    def workload_snapshot_cli(self, workload_id, is_full):
        self.created = False
        command_execution = ''
        snapshot_execution = ''
        if is_full:
            create_snapshot = command_argument_string.snapshot_create + workload_id
            LOG.debug("Create snapshot command: " + str(create_snapshot))
        else:
            create_snapshot = command_argument_string.incr_snapshot_create + workload_id
            LOG.debug("Create snapshot command: " + str(create_snapshot))

        rc = cli_parser.cli_returncode(create_snapshot)
        if rc != 0:
            LOG.debug("Execution of workload-snapshot command failed")
            command_execution = 'fail'
        else:
            LOG.debug("Command executed correctly for workload snapshot")
            command_execution = 'pass'

        snapshot_id = query_data.get_inprogress_snapshot_id(workload_id)
        LOG.debug("Snapshot ID: " + str(snapshot_id))
        wc = self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
        if (str(wc) == "available"):
            snapshot_execution = 'pass'
            self.created = True
        else:
            if (str(wc) == "error"):
                pass
        if (self.created == False):
            if is_full:
                snapshot_execution = 'pass'
            else:
                snapshot_execution = 'fail'

        if (tvaultconf.cleanup):
            self.addCleanup(self.snapshot_delete, workload_id, snapshot_id)
        return(snapshot_id, command_execution, snapshot_execution)

    '''
    This method takes restore details as a parameter rest_details. For selective restore key,values of rest_details are : 1. rest_type:selective 2. network_id
    3. subnet_id and 4. instances:{vm_id1:[list of vols associated with it including boot volume if any], vm_id2:[],...}.
    For inplace restore necessary key,values are : 1.rest_type:inplace and 2.instances:{vm_id1:[list of vols associated with it including boot volume if any], vm_id2:[],...}.
    '''

    def create_restore_json(self, rest_details):
        if rest_details['rest_type'] == 'selective':
            snapshot_network = {
                'id': rest_details['network_id'],
                'subnet': {'id': rest_details['subnet_id']}
                }
            target_network = {'id': rest_details['network_id'],
                              'subnet': {'id': rest_details['subnet_id']}
                              }
            network_details = [{'snapshot_network': snapshot_network,
                                'target_network': target_network}]
            LOG.debug("Network details for restore: " + str(network_details))
            instances = rest_details['instances']
            instance_details = []
            for instance in instances:
                temp_vdisks_data = []
                for volume in instances[instance]:
                    temp_vdisks_data.append(
                        {
                            'id': volume,
                            'availability_zone': CONF.volume.volume_availability_zone,
                            'new_volume_type': CONF.volume.volume_type})
                vm_name = "tempest_test_vm_" + instance + "_selectively_restored"
                temp_instance_data = {
                    'id': instance,
                    'availability_zone': CONF.compute.vm_availability_zone,
                    'include': True,
                    'restore_boot_disk': True,
                    'name': vm_name,
                    'vdisks': temp_vdisks_data}
            instance_details.append(temp_instance_data)
            LOG.debug("Instance details for restore: " + str(instance_details))
            payload = {'instance_details': instance_details,
                       'network_details': network_details}
            return(payload)

        elif rest_details['rest_type'] == 'inplace':
            instances = rest_details['instances']
            instance_details = []
            for instance in instances:
                temp_vdisks_data = []
                for volume in instances[instance]:
                    temp_vdisks_data.append(
                        {
                            'id': volume,
                            'availability_zone': CONF.volume.volume_availability_zone,
                            'new_volume_type': CONF.volume.volume_type})
                temp_instance_data = {
                    'id': instance,
                    'availability_zone': CONF.compute.vm_availability_zone,
                    'include': True,
                    'restore_boot_disk': True,
                    'vdisks': temp_vdisks_data}
            instance_details.append(temp_instance_data)
            LOG.debug("Instance details for restore: " + str(instance_details))
            payload = {
                'name': 'Inplace Restore',
                'zone': '',
                'oneclickrestore': False,
                'openstack': {
                    'instances': instance_details,
                    'networks_mapping': {
                        'networks': []}},
                'restore_type': 'inplace',
                'type': 'openstack',
                }
            return(payload)
        else:
            return

    '''
    This method lists the available types of WLM Quotas
    '''
    def get_quota_type(self):
        resp, body = self.wlm_client.client.get(
            "/project_quota_types")
        LOG.debug("get_quota_type response: %s", resp.content)
        if(resp.status_code != 200):
            resp.raise_for_status()
        quota_types = json.loads(resp.content)
        return quota_types['quota_types']
