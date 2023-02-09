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
import io
import subprocess
import shlex

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
from tempest import reporting
from tempest.lib.common.utils import data_utils

CONF = config.CONF
LOG = logging.getLogger(__name__)


class BaseWorkloadmgrTest(tempest.test.BaseTestCase):
    _api_version = 2
    uri_prefix = "v2.0"
    force_tenant_isolation = False
    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(BaseWorkloadmgrTest, cls).setup_clients()
        cls.subnets_client = cls.os_primary.subnets_client
        cls.wlm_client = cls.os_primary.wlm_client
        cls.servers_client = cls.os_primary.servers_client
        cls.interfaces_client = cls.os_primary.interfaces_client
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
        cls.images_client = cls.os_primary.image_client_v2
        cls.volumes_client = cls.os_primary.volumes_v3_client
        cls.volume_types_client = cls.os_primary.volume_types_client_latest
        cls.volumes_client.service = 'volumev3'
        cls.secret_client = cls.os_primary.secret_client
        cls.container_client = cls.os_primary.barbican_container_client
        cls.order_client = cls.os_primary.order_client
        cls.projects_client = cls.os_primary.projects_client
        cls.roles_client = cls.os_primary.roles_v3_client
        cls.users_client = cls.os_primary.users_v3_client

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
        LOG.debug("workload id: %s , show_workload Response: %s" % (workload_id,
                                                                    resp.content))
        if resp.status_code != 200:
            resp.raise_for_status()
        return workload_status

    '''
    Method returns the current status of a given snapshot
    '''

    def getSnapshotStatus(self, workload_id, snapshot_id):
        resp, body = self.wlm_client.client.get(
            "/workloads/" + workload_id + "/snapshots/" + snapshot_id)
        snapshot_status = body['snapshot']['status']
        LOG.debug("workload id: %s , snapshot id: %s , show_snapshot Response: "
                  "%s" % (workload_id, snapshot_id, resp.content))
        if resp.status_code != 200:
            resp.raise_for_status()
        return snapshot_status

    '''
    Method returns the current status of a given restore
    '''

    def getRestoreStatus(self, workload_id, snapshot_id, restore_id):
        resp, body = self.wlm_client.client.get(
            "/workloads/" + str(workload_id) + "/snapshots/" + str(snapshot_id) + "/restores/" + str(restore_id))
        restore_status = body['restore']['status']
        LOG.debug("workload id: %s , snapshot id: %s , restore id: %s , "
                  "show_restore Response: %s" % (workload_id, snapshot_id,
                                                 restore_id, resp.content))
        if resp.status_code != 200:
            resp.raise_for_status()
        return restore_status

    '''
    Method returns the schedule status of a given workload
    '''

    def getSchedulerStatus(self, workload_id):
        resp, body = self.wlm_client.client.get("/workloads/" + workload_id)
        schedule_status = body['workload']['jobschedule']['enabled']
        LOG.debug("workload id: %s , show_workload Response: %s" % (workload_id,
                                                                    resp.content))
        if resp.status_code != 200:
            resp.raise_for_status()
        return schedule_status

    '''
    Method returns the Retention Policy Type status of a given workload
    '''

    def getRetentionPolicyTypeStatus(self, workload_id):
        resp, body = self.wlm_client.client.get("/workloads/" + workload_id)
        retention_policy_type = body['workload']['jobschedule']['retention_policy_type']
        LOG.debug("workload id: %s , show_workload Response: %s" % (workload_id,
                                                                    resp.content))
        if resp.status_code != 200:
            resp.raise_for_status()
        return retention_policy_type

    '''
    Method returns the Retention Policy Value of a given workload
    '''

    ####### import pdb; pdb.set_trace()
    def getRetentionPolicyValueStatus(self, workload_id):
        resp, body = self.wlm_client.client.get("/workloads/" + workload_id)
        retention_policy_value = body['workload']['jobschedule']['retention_policy_value']
        LOG.debug("#### workloadid: %s , operation:show_workload" %
                  workload_id)
        LOG.debug("Response:" + str(resp.content))
        if (resp.status_code != 200):
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
        if (resp.status_code != 200):
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
        if (user_data != "NULL"):
            with open(user_data, 'rb') as tmp_userdata:
                user_data = base64.b64encode(tmp_userdata.read())
        else:
            user_data = base64.b64encode(b' ')
        if (vm_name == ""):
            ts = str(datetime.now())
            vm_name = "Test_Tempest_Vm" + ts.replace('.', '-')
        if (tvaultconf.vms_from_file and self.is_vm_available()):
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
        if (tvaultconf.cleanup and vm_cleanup):
            self.addCleanup(self.delete_vm, server_id)
        return server_id

    '''
    Method returns the Instance IDs of the new VM instances created
    '''

    def create_vms(self, totalVms):
        instances = []
        for vm in range(0, totalVms):
            if (tvaultconf.vms_from_file):
                flag = 0
                flag = self.is_vm_available()
                if (flag != 0):
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
        if (tvaultconf.cleanup):
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
            waiters.wait_for_server_termination(self.servers_client, server_id,
                    ignore_error=True)
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
        if (tvaultconf.volumes_from_file):
            flag = 0
            flag = self.is_volume_available()
            if (flag != 0):
                volume_id = self.read_volume_id()
            else:
                if (image_id != ""):
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
            if (image_id != ""):
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
        if (tvaultconf.cleanup and volume_cleanup):
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
    Method returns the list of attached volumes to a given VM instance
    '''

    def get_attached_volumes_info(self, volume_id):
        volume = self.volumes_client.show_volume(volume_id)['volume']['volume_type']
        LOG.debug("Attached volumes: " + str(volume))
        return volume

    '''
    Method deletes the given volumes list
    '''

    def delete_volumes(self, volumes):
        for volume in volumes:
            try:
                self.delete_volume(volume)
                LOG.debug('Volume delete operation completed %s' % volume)
            except Exception as e:
                LOG.error("Exception" + str(e))
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
        if (not tvaultconf.workloads_from_file):
            if (tvaultconf.volumes_from_file):
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
        if (tvaultconf.cleanup and attach_cleanup):
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
    Method to update volume metadaa
    '''
    def modify_volume_metadata(self, volume_id, metadata_tag_name):
        body = ""
        try:
            body = self.volumes_client.update_volume_metadata(
                volume_id, metadata_tag_name)['metadata']

        except Exception as e:
            LOG.error("Exception" + str(e))
            pass

        return body

    '''
    Method creates a workload and returns Workload id
    '''

    def workload_create(
            self,
            instances,
            jobschedule={"enabled": False},
            workload_name="",
            workload_cleanup=True,
            encryption=False,
            secret_uuid="",
            description='test'):
        if (tvaultconf.workloads_from_file):
            flag = 0
            flag = self.is_workload_available()
            if (flag != 0):
                workload_id = self.read_workload_id()
            else:
                in_list = []
                ts = str(datetime.now())
                workload_name = "tempest" + ts.replace('.', '-')
                for id in instances:
                    in_list.append({'instance-id': id})
                payload = {'workload': {'name': workload_name,
                                        'source_platform': 'openstack',
                                        'instances': in_list,
                                        'jobschedule': jobschedule,
                                        'metadata': {},
                                        'description': description,
                                        'encryption': encryption,
                                        'secret_uuid': secret_uuid}}

                resp, body = self.wlm_client.client.post(
                    "/workloads", json=payload)
                workload_id = body['workload']['id']
                LOG.debug(
                    "#### workloadid: %s , operation:workload_create" %
                    workload_id)
                LOG.debug("Response:" + str(resp.content))
                if (resp.status_code != 202):
                    resp.raise_for_status()
        else:
            in_list = []
            if (workload_name == ""):
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
                                    'description': description,
                                    'encryption': encryption,
                                    'secret_uuid': secret_uuid}}

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
            if (resp.status_code != 202):
                resp.raise_for_status()
        LOG.debug('WorkloadCreated: %s' % workload_id)
        if (tvaultconf.cleanup and workload_cleanup):
            self.addCleanup(self.workload_delete, workload_id)
        return workload_id

    '''
    Method deletes a given workload
    '''

    def workload_delete(self, workload_id):
        try:
            self.wait_for_workload_tobe_available(workload_id)

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
            LOG.error(f"Exception in workload_delete: {e}")
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
        if (is_full):
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
        if (tvaultconf.cleanup and snapshot_cleanup):
            self.addCleanup(self.snapshot_delete, workload_id, snapshot_id)
        return snapshot_id

    '''
    Method resets the given workload
    '''

    def workload_reset(self, workload_id):
        try:
            self.wait_for_workload_tobe_available(workload_id)
            resp, body = self.wlm_client.client.post(
                "/workloads/" + workload_id + "/reset")
            LOG.debug("#### workloadid: %s, operation: workload-reset " %
                      workload_id)
            LOG.debug("Response:" + str(resp.content))
            LOG.debug("Response code:" + str(resp.status_code))
            if (resp.status_code != 202):
                resp.raise_for_status()
            return True
        except Exception as e:
            LOG.error("Exception in workload_reassign: " + str(e))
            return False

    '''
    Method to do workload reassign
    '''

    def workload_reassign(self, new_tenant_id, workload_ids, user_id):
        try:
            payload = [{"workload_ids": [workload_ids],
                        "migrate_cloud": False,
                        "old_tenant_ids": [],
                        "user_id": user_id,
                        "new_tenant_id": new_tenant_id}]
            resp, body = self.wlm_client.client.post(
                "/workloads/reasign_workloads", json=payload)
            reassignstatus = body['workloads']['reassigned_workloads'][0]['status']
            LOG.debug("Response:" + str(resp.content))
            if (resp.status_code != 200):
                resp.raise_for_status()
            else:
                if reassignstatus == "available":
                    return (0)
        except Exception as e:
            LOG.error("Exception in workload_reassign: " + str(e))

    '''
    Method to wait until the workload is available
    '''

    def wait_for_workload_tobe_available(self, workload_id, timeout=7200):
        status = "available"
        start_time = int(time.time())
        LOG.debug('Checking workload status')
        while (status != self.getWorkloadStatus(workload_id)):
            if (self.getWorkloadStatus(workload_id) == 'error'):
                LOG.debug('workload status is: %s , workload create failed' %
                          self.getWorkloadStatus(workload_id))
                # raise Exception("Workload creation failed")
                return False
            if time.time() - start_time > timeout:
                LOG.error("Timeout Waiting for workload to be available")
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
        if (self.getSnapshotStatus(workload_id, snapshot_id) == 'available'):
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
        if (resp.status_code != 202):
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
            restore_cleanup=True,
            sec_group_cleanup=True):
        LOG.debug("At the start of snapshot_restore method")
        if (restore_name == ""):
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
        if (resp.status_code != 202):
            resp.raise_for_status()
        LOG.debug('Restore of snapshot %s scheduled succesffuly' % snapshot_id)
        self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
        self.restored_vms = self.get_restored_vm_list(restore_id)
        self.restored_volumes = self.get_restored_volume_list(restore_id)
        self.restored_secgrps = self.getRestoredSecGroupPolicies(self.restored_vms)
        if (tvaultconf.cleanup and restore_cleanup):
            # self.restored_vms = self.get_restored_vm_list(restore_id)
            # self.restored_volumes = self.get_restored_volume_list(restore_id)
            if sec_group_cleanup:
                for each in self.restored_secgrps:
                    self.restored_security_group_id = self.get_restored_security_group_id_by_name(each)
                    self.addCleanup(self.delete_security_group, self.restored_security_group_id)
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
            sec_group_cleanup=True):
        LOG.debug("At the start of snapshot_selective_restore method")
        if (restore_name == ""):
            restore_name = "Tempest_test_restore"
        if (restore_desc == ""):
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
            # self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            resp, body = self.wlm_client.client.post(
                "/workloads/" + workload_id + "/snapshots/" + snapshot_id + "/restores", json=payload)
            restore_id = body['restore']['id']
            LOG.debug(
                "#### workloadid: %s ,snapshot_id: %s , restore_id: %s , operation: snapshot_restore" %
                (workload_id, snapshot_id, restore_id))
            LOG.debug("Response:" + str(resp.content))
            if (resp.status_code != 202):
                resp.raise_for_status()
            LOG.debug('Restore of snapshot %s scheduled succesffuly' %
                      snapshot_id)
            if (tvaultconf.cleanup and restore_cleanup):
                self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
                self.restored_vms = self.get_restored_vm_list(restore_id)
                self.restored_volumes = self.get_restored_volume_list(
                    restore_id)
                self.restored_secgrps = self.getRestoredSecGroupPolicies(self.restored_vms)
                self.addCleanup(self.restore_delete,
                                workload_id, snapshot_id, restore_id)
                if sec_group_cleanup:
                    for each in self.restored_secgrps:
                        self.restored_security_group_id = self.get_restored_security_group_id_by_name(each)
                        self.addCleanup(self.delete_security_group, self.restored_security_group_id)
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
    Method returns the list of restored volumes id an type
    '''

    def get_restored_volume_info_list(self, restore_id):
        instances = self.get_restored_vm_list(restore_id)
        volume_info_list = []
        for instance in instances:
            LOG.debug("instance:" + instance)
            if len(self.get_attached_volumes(instance)) > 0:
                for volume in self.get_attached_volumes(instance['id']):
                    volume_info_list.append(self.get_attached_volumes_info(volume))
        LOG.debug("restored volume info list:" + str(volume_info_list))
        return volume_info_list

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

    def wait_for_snapshot_tobe_available(self, workload_id, snapshot_id, timeout=7200):
        status = "available"
        LOG.debug('Checking snapshot status')
        start_time = int(time.time())
        while (status != self.getSnapshotStatus(workload_id, snapshot_id)):
            if (self.getSnapshotStatus(workload_id, snapshot_id) == 'error'):
                LOG.debug('Snapshot status is: %s' %
                          self.getSnapshotStatus(workload_id, snapshot_id))
                raise Exception("Snapshot creation failed")
            if time.time() - start_time > timeout:
                LOG.error("Timeout Waiting for snapshot to be available")
                return False
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
        if (self.getRestoreStatus(workload_id, snapshot_id, restore_id) == 'available'):
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
                if (SnapshotNameInfo == 'jobscheduler'):
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
                if (SnapshotNameInfo == 'jobscheduler' and (str(tdelta) == "1:00:00")):
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
        self.wait_for_snapshot_tobe_available(workload_id, snapshot_id,timeout=1800)
        resp, body = self.wlm_client.client.delete(
            "/workloads/" + workload_id + "/snapshots/" + snapshot_id + "/restores/" + restore_id)
        LOG.debug(
            "#### workloadid: %s ,snapshot_id: %s  , Operation: restore_delete" %
            (workload_id, snapshot_id))
        LOG.debug("Response:" + str(resp.content))
        if (resp.status_code != 202):
            resp.raise_for_status()
        self.wait_for_snapshot_tobe_available(workload_id, snapshot_id,timeout=1800)
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
        if (workload_id is not None):
            resp, body = self.wlm_client.client.get(
                "/snapshots?workload_id=" + workload_id)
        else:
            resp, body = self.wlm_client.client.get("/snapshots")
        snapshot_list = []
        for i in range(0, len(body['snapshots'])):
            snapshot_list.append(body['snapshots'][i]['id'])
        LOG.debug("Response:" + str(resp.content))
        if (resp.status_code != 200):
            resp.raise_for_status()
        return snapshot_list

    '''
    Method returns the snapshot list information with "no error" status
    '''

    def getSnapshotListWithNoError(self, workload_id=None):
        if (workload_id is not None):
            resp, body = self.wlm_client.client.get(
                "/snapshots?workload_id=" + workload_id)
        else:
            resp, body = self.wlm_client.client.get("/snapshots")
        snapshot_list = []
        for i in range(0, len(body['snapshots'])):
            if(body['snapshots'][i]['status'] == "available"):
                snapshot_list.append(body['snapshots'][i]['id'])
        LOG.debug("Response:" + str(resp.content))
        if (resp.status_code != 200):
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
        snapshot_error_msg = body['snapshot']['error_msg']
        snapshot_info.append(snapshot_error_msg)
        LOG.debug('snapshot error msg is : %s' % snapshot_info[3])
        LOG.debug("Response:" + str(resp.content))
        if (resp.status_code != 200):
            resp.raise_for_status()
        return snapshot_info

    '''
    Method returns the snapshot information . It return array with create time,name and type information for given snapshot
    '''

    def getSnapshotVmVolumeInfo(self, snapshot_id='none'):
        resp, body = self.wlm_client.client.get("/snapshots/" + snapshot_id)
        snapshot_info = {}
        for instance in body['snapshot']['instances']:
            volumes = []
            for volume in instance['vdisks']:
                if "volume_id" in volume.keys():
                    volumes.append(volume['volume_id'])
            snapshot_info[instance['id']] = volumes
        LOG.debug("Response:" + str(resp.content))
        if (resp.status_code != 200):
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

    def get_floating_ips(self, project_id=CONF.identity.tenant_id):
        floating_ips_list = []
        get_ips_response = self.floating_ips_client.list_floatingips(project_id=project_id)
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
        if (tvaultconf.cleanup and floatingip_cleanup):
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
            if (flag):
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
            if (flag):
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
            mount_points,
            partition=1,
            size=""):
        self.channel = ssh.invoke_shell()
        commands = []
        for volume in volumes:
            commands.extend(["sudo fdisk {}".format(volume),
                             "n",
                             "p",
                             "",
                             "",
                             str(size),
                             "w",
                             "sudo fdisk -l {0}{1}".format(volume, partition)])
            # "yes | sudo mkfs -t ext3 {}1".format(volume)])

        for command in commands:
            LOG.debug("Executing fdisk: " + str(command))
            self.channel.send(command + "\n")
            time.sleep(5)
            while not self.channel.recv_ready():
                time.sleep(3)

            output = self.channel.recv(9999)
            LOG.debug(str(output))
        time.sleep(10)
        for volume in volumes:
            cmd = "sudo mkfs -t ext3 {0}{1}".format(volume, partition)
            LOG.debug("Executing mkfs : " + str(cmd))
            stdin, stdout, stderr = ssh.exec_command(cmd)
            time.sleep(5)
            while not stdout.channel.exit_status_ready():
                time.sleep(3)
            LOG.debug("mkfs output:  " + str(stdout.readlines()))
            LOG.debug("mkfs error:  " + str(stderr.readlines()))

    '''
    disks mounting
    '''

    def execute_command_disk_mount(
            self,
            ssh,
            ipAddress,
            volumes,
            mount_points, partition=1):
        LOG.debug("Execute command disk mount connecting to " + str(ipAddress))

        self.channel = ssh.invoke_shell()
        for i in range(len(volumes)):

            commands = [
                "sudo mkdir " +
                mount_points[i],
                "sudo mount {0}{1} {2}".format(
                    volumes[i],partition,
                    mount_points[i]),
                "sudo df -h",
                "pwd"]

            for command in commands:
                LOG.debug("Executing disk mount: " + str(command))
                stdin, stdout, stderr = ssh.exec_command(command)
                time.sleep(5)
                while not stdout.channel.exit_status_ready():
                    time.sleep(3)
                LOG.debug("disk mount command output:  " + str(stdout.readlines()))
                LOG.debug("disk mount command error:  " + str(stderr.readlines()))
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
            LOG.error("Exception in addCustomSizedfilesOnLinux: " + str(e))

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
                start_time = time.time()
                while not stdout.channel.exit_status_ready():
                    LOG.debug("Waiting for creation of File_%s", str(count + 1))
                    if time.time() - start_time > 180:
                        LOG.debug("Timeout Waiting for file creation on VM")
                        raise Exception(
                            "Timeout Waiting for file creation on VM")
                        break
                    time.sleep(5)
                cmdFileSize = "sudo du -s " + str(dirPath) + "/File_" + str(count + 1)
                LOG.debug("Executing command -> " + cmdFileSize)
                stdin, stdout, stderr = ssh.exec_command(cmdFileSize)
                output = stdout.readlines()
                print(output)
                for line in output:
                    LOG.debug(str(dirPath) + "/File_" + str(count + 1) + " created of size " + str(
                        line.split("['")[0].split("\t")[0]) + "KB")
            time.sleep(10)
        except Exception as e:
            LOG.error("Exception in addCustomfilesOnLinuxVM: " + str(e))
            raise Exception(
                "addCustomfilesOnLinuxVM Failed")

    '''
    calculate md5 checksum
    '''

    def calculatemmd5checksum(self, ssh, dirPath):
        local_md5sum = ""
        buildCommand = "sudo find " + \
                       str(dirPath) + "/ -type f -not -path '*/.*' -exec md5sum {} +"
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

    def create_key_pair(self, keypair_name=tvaultconf.key_pair_name,
                        keypair_cleanup=True):
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
        if (tvaultconf.cleanup and keypair_cleanup):
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
            if (str(floatingips['floatingips'][i]['floating_ip_address']) == str(floating_ip)):
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
            if (str(floatingips['floatingips'][i]['floating_ip_address']) == str(floating_ip)):
                port_id = floatingips['floatingips'][i]['port_id']
                LOG.debug("port id for :" + str(floating_ip) +
                          " is: " + str(port_id))
        return port_id

    '''
    Method to get key pair details
    '''

    def get_key_pair_details(self, keypair_name):
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
            if len(port['fixed_ips']) and \
                    str(port['fixed_ips'][0]['ip_address']) == str(fixed_ip):
                return str(port['id'])

    '''delete port'''

    def delete_port(self, server_id):
        ports = []
        vm_details = self.get_vm_details(server_id)
        if vm_details['server']['status'] != 'ERROR':
            int_net_name = \
                    str(list(vm_details['server']['addresses'].keys())[0])
            fixed_ip = \
                str(vm_details['server']['addresses'][int_net_name][0]['addr'])
            ports.append(self.get_port_id(fixed_ip))
            LOG.debug("Port deletion for " + str(ports) + " started.")
            self.delete_ports(ports)

    '''create_security_group in same/another project'''

    def create_security_group(self, name, description, tenant_id=CONF.identity.tenant_id, secgrp_cleanup=True):
        self.security_group_id = self.security_groups_client.create_security_group(
            name=name, description=description, tenant_id=tenant_id)['security_group']['id']
        if (tvaultconf.cleanup and secgrp_cleanup):
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
            LOG.debug("security group id for security group {}".format(security_group_id))
            return security_group_id
        else:
            LOG.debug("security group id is NOT present/restored")
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
        flavor_list = self.flavors_client.list_flavors()['flavors']
        LOG.debug("Flavor list: " + str(flavor_list))
        fl_id = None
        for fl in flavor_list:
            if fl['name'] == name:
                fl_id = fl['id']
                break
        if fl_id:
            LOG.debug("flavor already exists with same name")
            self.delete_flavor(fl_id)
        else:
            LOG.debug("flavor does not exist with same name")

        if (ephemeral == 0):
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
        if (tvaultconf.cleanup and flavor_cleanup):
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
            if (flavor_list[i]['name'] == flavor_name):
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
        if (resp.status_code != 200):
            resp.raise_for_status()
        return workload_list

    '''
    Method to fetch global job scheduler status
    '''

    def get_global_job_scheduler_status(self):
        resp, body = self.wlm_client.client.get("/global_job_scheduler")
        LOG.debug("Response:" + str(resp.content))
        if (resp.status_code != 200):
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
        if (resp.status_code != 200):
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
        if (resp.status_code != 200):
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
            if (flag):
                return flag
            else:
                return msg

    '''
    Method to fetch license list
    '''

    def get_license_list(self):
        resp, body = self.wlm_client.client.get("/workloads/metrics/license")
        LOG.debug("Response:" + str(resp.content))
        if (resp.status_code != 200):
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
        if (resp.status_code != 200):
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
        if (resp.status_code != 200):
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
        if (resp.status_code != 202):
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
        if (resp.status_code != 200):
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
                                    if len(v4) != 0:
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
                                    if path1 in v2:
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
            mount_cleanup=True, timeout=7200):
        try:
            payload = {"mount": {"mount_vm_id": vm_id,
                                 "options": {}}}
            resp, body = self.wlm_client.client.post(
                "/snapshots/" + snapshot_id + "/mount", json=payload)
            LOG.debug("#### Mounting of snapshot is initiated: ")
            if (resp.status_code != 200):
                resp.raise_for_status()
            is_successful = self.wait_for_snapshot_tobe_mounted(workload_id,snapshot_id,timeout=timeout)
            if (tvaultconf.cleanup and mount_cleanup):
                self.addCleanup(self.unmount_snapshot, workload_id, snapshot_id)
        except Exception as e:
            LOG.error('Snapshot mount failed with error: %s' % snapshot_id)
            is_successful = False
        return is_successful

    '''
    Method to wait for snapshot to be mounted and return the status
    '''

    def wait_for_snapshot_tobe_mounted(
            self,
            workload_id,
            snapshot_id, timeout=7200):
        is_successful = True
        LOG.debug("Getting snapshot mount status")
        start_time = int(time.time())
        while (self.getSnapshotStatus(workload_id, snapshot_id) != "mounted"):
            if (self.getSnapshotStatus(workload_id, snapshot_id) == "available"):
                LOG.debug('Snapshot status is: %s' %
                          self.getSnapshotStatus(workload_id, snapshot_id))
                is_successful = False
                return is_successful
            if time.time() - start_time > timeout:
                LOG.error("Timeout Waiting for snapshot to be mounted")
                is_successful = False
                return is_successful
            LOG.debug('snapshot mount status is: %s , sleeping for 30 sec' %
                      self.getSnapshotStatus(workload_id, snapshot_id))
            time.sleep(30)
        return is_successful

    '''
    Method to verify mount snapshot and return the status
    '''

    def verify_snapshot_mount(
            self,
            floating_ip,
            fvm_image):
        is_successful = False
        fvm_ssh_user = ""
        if "centos" in fvm_image:
            fvm_ssh_user = "centos"
        elif "ubuntu" in fvm_image:
            fvm_ssh_user = "ubuntu"
        LOG.debug("validate that snapshot is mounted on FVM " + fvm_ssh_user)
        ssh = self.SshRemoteMachineConnectionWithRSAKey(
            floating_ip, fvm_ssh_user)  # CONF.validation.fvm_ssh_user
        output_list = self.validate_snapshot_mount(ssh).decode('UTF-8').split('\n')
        ssh.close()
        flag = 0
        flag1 = 0
        flag2 = 0
        for i in output_list:
            LOG.debug("i= " + str(i))
            if ('vdb1.mnt' in i) and ('image' in i):
                LOG.debug(
                    "connect to fvm and check mountpoint for image instance is mounted on FVM instance")
                flag1 = 1
                if 'File_1' in i:
                    LOG.debug("Image instance file exists on mounted snapshot")
                    is_successful = True
                else:
                    LOG.debug("Image instance file does not exists on FVM instance")
                    is_successful = False
                    # raise Exception("Image instance file does not found on FVM instance")
            elif ('vdb1.mnt' in i) and ('volume' in i):
                LOG.debug(
                    "connect to fvm and check mountpoint for volume instance is mounted on FVM instance")
                flag2 = 1
                if 'File_1' in i:
                    LOG.debug("Volume instance file exists on mounted snapshot")
                    is_successful = True
                else:
                    LOG.debug("Volume instance file does not exists on FVM instance")
                    is_successful = False
                    # raise Exception("Volume instance file not found on FVM instance")
            else:
                pass
        if (flag1 == 0) or (flag2 == 0):
            LOG.debug(
                "mount snapshot is unsuccessful on FVM")
            LOG.debug("file not found on FVM instance")
        elif (flag1 == 1) and (flag2 == 1):
            flag = 1
        return is_successful, flag

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
            LOG.error('Snapshot unmount failed: %s' % snapshot_id)
            return False

    '''
    Method to verify unmount snapshot and return the status
    '''

    def verify_snapshot_unmount(
            self,
            floating_ip,
            fvm_image):
        is_successful = False
        fvm_ssh_user = ""
        if "centos" in fvm_image:
            fvm_ssh_user = "centos"
        elif "ubuntu" in fvm_image:
            fvm_ssh_user = "ubuntu"
        LOG.debug("validate that snapshot is unmounted from FVM")
        ssh = self.SshRemoteMachineConnectionWithRSAKey(
            floating_ip, fvm_ssh_user)  # CONF.validation.fvm_ssh_user
        output_list = self.validate_snapshot_mount(ssh)
        ssh.close()

        if output_list == b'':
            LOG.debug("Unmounting successful")
            is_successful = True
        else:
            LOG.debug("Unmounting unsuccessful")
            # raise Exception("Unmounting of a snapshot failed")
        return is_successful

    '''
    Method to add newadmin role and newadmin_api rule to 
    "workload:get_storage_usage" operation and "workload:get_nodes" 
    operations in policy.yaml file on tvault. 
    Method to add backup role and backup_api rule to "snapshot_create", 
    "snapshot_delete", "workload_create", "workload_delete", "restore_create", 
    "restore_delete" operation and "workload:get_nodes" operations in 
    policy.yaml file on tvault
    '''

    def change_policyyaml_file(self, role, rule, policy_changes_cleanup=True):
        if len(tvaultconf.tvault_ip) == 0:
            raise Exception("Tvault IPs not available")
        for ip in tvaultconf.tvault_ip:
            ssh = self.SshRemoteMachineConnection(ip, tvaultconf.tvault_username,
                                                  tvaultconf.tvault_password)
            if role == "newadmin":
                old_rule = "admin_api"
                LOG.debug("Add %s role in policy.yaml", role)
                operations = ["workload:get_storage_usage", "workload:get_nodes"]

            elif role == "backup":
                old_rule = "admin_or_owner"
                LOG.debug("Add %s role in policy.yaml", role)
                operations = ["workload:workload_snapshot", "snapshot:snapshot_delete", "workload:workload_create",
                              "workload:workload_delete", "snapshot:snapshot_restore", "restore:restore_delete"]

            role_add_command = 'sed -i \'1s/^/{0}:\\n- - role:{1}\\n/\' /etc/workloadmgr/policy.yaml'.format(
                rule, role)
            rule_assign_command = ""
            for op in operations:
                rule_assign_command += '; ' + 'sed -i \'/{1}/c {1}: rule:{0}\'\
                /etc/workloadmgr/policy.yaml'.format(rule, op)
            LOG.debug("role_add_command: %s ;\n rule_assign_command: %s", role_add_command, rule_assign_command)
            commands = role_add_command + rule_assign_command
            LOG.debug("Commands to add role: %s", commands)
            stdin, stdout, stderr = ssh.exec_command(commands)
            if (tvaultconf.cleanup and policy_changes_cleanup):
                self.addCleanup(self.revert_changes_policyyaml, old_rule)
            ssh.close()

    '''
    Method to revert changes of role and rule in policy.json file on tvault
    Method to delete newadmin role and newadmin_api rule was assigned to 
    "workload:get_storage_usage" operation and "workload:get_nodes" operations 
    in policy.yaml file on tvault.
    Method to delete backup role and backup_api rule was assigned to 
    "snapshot_create", "snapshot_delete", "workload_create", "workload_delete",
    "restore_create", "restore_delete" and "workload:get_nodes" operations in 
    policy.yaml file on tvault
    '''

    def revert_changes_policyyaml(self, rule):
        if len(tvaultconf.tvault_ip) == 0:
            raise Exception("Tvault IPs not available")
        for ip in tvaultconf.tvault_ip:
            ssh = self.SshRemoteMachineConnection(ip, tvaultconf.tvault_username,
                                                  tvaultconf.tvault_password)
            if rule == "admin_api":
                role = "newadmin_api"
                operations = ["workload:get_storage_usage", "workload:get_nodes"]

            elif rule == "admin_or_owner":
                role = "backup_api"
                operations = ["workload:workload_snapshot", "snapshot:snapshot_delete", "workload:workload_create",
                              "workload:workload_delete", "snapshot:snapshot_restore", "restore:restore_delete"]

            role_delete_command = "sed -i '/^{0}/,+1d' /etc/workloadmgr/policy.yaml".format(role)
            rule_reassign_command = ""
            for op in operations:
                rule_reassign_command += '; ' + 'sed -i \'/{1}/c {1}: rule:{0}\'\
                /etc/workloadmgr/policy.yaml'.format(rule, op)
            LOG.debug("role_delete_command: %s ;\n rule_reassign_command: %s", \
                      role_delete_command, rule_reassign_command)
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
        if (resp.status_code != 200):
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
        if (resp.status_code != 200):
            resp.raise_for_status()
        return setting_data

    '''
    Method to fetch trilioVault email settings
    '''

    def get_settings_list(self):
        resp, body = self.wlm_client.client.post("/workloads/settings")
        setting_list = body['settings']
        LOG.debug("List Setting Response:" + str(resp.content))
        if (resp.status_code != 200):
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
        if (resp.status_code != 200):
            # resp.raise_for_status()
            return False
        return True

    '''
    Method returns the restore list information
    '''

    def getRestoreList(self, snapshot_id=None):
        if (snapshot_id is not None):
            resp, body = self.wlm_client.client.get(
                "/restores?snapshot_id=" + snapshot_id)
        else:
            resp, body = self.wlm_client.client.get("/restores")
        restore_list = []
        for i in range(0, len(body['restores'])):
            restore_list.append(body['restores'][i]['id'])
        LOG.debug("Response:" + str(resp.content))
        if (resp.status_code != 200):
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
        if (resp.status_code != 200):
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
            if (resp.status_code != 200):
                resp.raise_for_status()
            return body
        except Exception as e:
            LOG.error("Exception in getTenantChargeback: " + str(e))
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
            if (resp.status_code != 200):
                resp.raise_for_status()
            return body
        except Exception as e:
            LOG.error("Exception in getVMProtected: " + str(e))
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
            if (resp.status_code != 200):
                resp.raise_for_status()
            return body
        except Exception as e:
            LOG.error("Exception in getTenantUsage: " + str(e))
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
        if (resp.status_code != 202):
            resp.raise_for_status()

        LOG.debug('PolicyCreated: %s' % policy_id)
        if (tvaultconf.cleanup and policy_cleanup):
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
            if (resp.status_code != 202):
                resp.raise_for_status()
            LOG.debug('PolicyUpdated: %s' % policy_id)
            return True
        except Exception as e:
            LOG.error('Policyupdate failed: %s' % policy_id)
            return False

    '''
    This method deletes workload policy and return status
    '''

    def workload_policy_delete(self, policy_id):
        try:
            details = self.get_policy_details(policy_id)
            list_of_project_assigned_to_policy = details[4]
            LOG.debug("list_of_project_assigned_to_policy:" + str(list_of_project_assigned_to_policy))
            # for i in range(len(list_of_project_assigned_to_policy)):
                # self.assign_unassign_workload_policy(
                    # policy_id, remove_project_ids_list=list_of_project_assigned_to_policy[i])
            self.assign_unassign_workload_policy(
                    policy_id, remove_project_ids_list=list_of_project_assigned_to_policy)
            resp, body = self.wlm_client.client.delete(
                "/workload_policy/" + policy_id)
            LOG.debug(
                "#### policy id: %s , operation: workload_policy_delete" %
                policy_id)
            LOG.debug("Response:" + str(resp.content))
            if (resp.status_code != 202):
                resp.raise_for_status()
            LOG.debug('WorkloadPolicyDeleted: %s' % policy_id)
            return True
        except Exception as e:
            LOG.error("Exception in workload_policy_delete: " + str(e))
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
            LOG.debug("Payload:" + str(payload))
            resp, body = self.wlm_client.client.post(
                "/workload_policy/" + policy_id + "/assign", json=payload)
            policy_id = body['policy']['id']
            LOG.debug(
                "#### policyid: %s , operation:assignorunassign_workload_policy" %
                policy_id)
            LOG.debug("Response:" + str(resp.content))
            LOG.debug("Response code:" + str(resp.status_code))
            if (resp.status_code != 200 or resp.status_code != 202):
                resp.raise_for_status()
            return True
        except Exception as e:
            LOG.error("Exception in assign_unassign_workload_policy: " + str(e))
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
            if (resp.status_code != 202):
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
            LOG.error("Exception in get_policy_details: " + str(e))
            return False

    '''
    Method to return policy-list, returns id's
    '''

    def get_policy_list(self):
        try:
            resp, body = self.wlm_client.client.get("/workload_policy/")
            LOG.debug("Response:" + str(resp.content))
            if (resp.status_code != 202):
                resp.raise_for_status()
            policy_list = []
            for i in range(len(body['policy_list'])):
                policy_id = body['policy_list'][i]['id']
                policy_list.append(policy_id)
            return policy_list
        except Exception as e:
            LOG.error("Exception in get_policy_list: " + str(e))
            return False

    '''
    Method returns mountpoint path of backup target media
    '''

    def get_mountpoint_path(self):
        cmd = (tvaultconf.command_prefix).replace("<command>","mount")
        p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        mountpoint_path = None
        for line in stdout.splitlines():
            if str(line).find('triliovault-mounts') != -1:
                mountpoint_path = str(line).split()[2]
        LOG.debug("mountpoint path is : " + str(mountpoint_path))
        return str(mountpoint_path)

    '''
    Method returns True if snapshot dir is exists on backup target media
    '''

    def check_snapshot_exist_on_backend(self, mount_path,
            workload_id, snapshot_id):
        cmd = (tvaultconf.command_prefix).replace("<command>","ls " + str(mount_path).strip() + \
                "/workload_" + str(workload_id).strip() + "/snapshot_" + \
                str(snapshot_id).strip())
        p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        LOG.debug(f"stdout: {stdout}; stderr: {stderr}")
        if str(stderr).find('No such file or directory') != -1:
            return False
        else:
            return True

    '''
    Method to return policies list assigned to particular project
    '''

    def assigned_policies(self, project_id):
        try:
            resp, body = self.wlm_client.client.get(
                "/workload_policy/assigned/" + project_id)
            LOG.debug("Response:" + str(resp.content))
            if (resp.status_code != 202):
                resp.raise_for_status()
            project_list_assigned_policies = []
            for i in range(len(body['policies'])):
                policy_id = body['policies'][i]['policy_id']
                project_list_assigned_policies.append(policy_id)
            return project_list_assigned_policies
        except Exception as e:
            LOG.error("Exception in assigned_policies: " + str(e))
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
        if (resp.status_code != 200):
            resp.raise_for_status()
        return workload_data

    '''
    Method to fetch trust list
    '''

    def get_trust_list(self):
        resp, body = self.wlm_client.client.get("/trusts")
        LOG.debug("Response:" + str(resp.content))
        if (resp.status_code != 200):
            resp.raise_for_status()
        data = body['trust']
        return data

    '''
    Method to restart wlm-api service on tvault
    '''

    def restart_wlm_api_service(self):
        if len(tvaultconf.tvault_ip) == 0:
            raise Exception("Tvault IPs not available")
        for ip in tvaultconf.tvault_ip:
            ssh = self.SshRemoteMachineConnection(ip, tvaultconf.tvault_username,
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
            file_name="File_1",
            disk_dir=""):
        try:
            time.sleep(20)
            cmd = "sudo su - root -c 'df -h'"
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
            LOG.debug("df -h output: %s", stdout.read())
            cmd = "sudo su - root -c 'ls -la " + file_path_to_search + "/Test_*/vda*" + disk_dir + "'"
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
            LOG.debug("In VDA List files output: %s ; list files error: %s", stdout.read(), stderr.read())
            cmd = "sudo su - root -c 'ls -la " + file_path_to_search + "/Test_*/vdb*'"
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
            LOG.debug("In VDB List files output: %s ; list files error: %s", stdout.read(), stderr.read())
            cmd = "sudo su - root -c 'ls -la " + file_path_to_search + "/Test_*/vdc*'"
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
            LOG.debug("In VDC List files output: %s ; list files error: %s", stdout.read(), stderr.read())
            buildCommand = "sudo su - root -c 'find " + file_path_to_search + " -name " + file_name + "'"
            LOG.debug("build command to search file is :" + str(buildCommand))
            stdin, stdout, stderr = ssh.exec_command(buildCommand, timeout=300)
            output = stdout.read()
            LOG.debug(output)
            return (bytes(output))
        except Exception as e:
            LOG.debug("Exception in validate_snapshot_mount: " + str(e))

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

    def delete_network(self, network_id, tenant_id=CONF.identity.tenant_id):
        ports_list = []
        router_id_list = []
        routers = self.routers_client.list_routers()['routers']
        routers = [x for x in routers if x['tenant_id'] ==
                   tenant_id]
        self.delete_router_routes(routers)
        router_id_list = [x['id']
                          for x in routers if x['tenant_id'] == tenant_id]
        for router in router_id_list:
            self.delete_router_interfaces(tenant_id)
        self.delete_routers(router_id_list)
        ports_list = self.get_port_list_by_network_id(network_id)
        self.delete_ports(ports_list)
        network_delete = self.networks_client.delete_network(network_id)

    '''
    Method to delete router interface
    '''

    def delete_router_interfaces(self, tenant_id=CONF.identity.tenant_id):
        interfaces = self.ports_client.list_ports()['ports']
        LOG.debug(f"interfaces returned: {interfaces}")
        for interface in interfaces:
            if interface['tenant_id'] == tenant_id and \
                interface['device_owner'] in \
                    ('network:router_interface', \
                     'network:ha_router_replicated_interface'):
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
        if (resp.status_code != 200):
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
        if (resp.status_code != 200):
            resp.raise_for_status()
        return storage_usage_list

    '''
    Method to delete entire network topology
    This method won't delete public network
    '''

    def delete_network_topology(self, tenant_id=CONF.identity.tenant_id):
        LOG.debug("Deleting the existing networks")
        networkslist = self.networks_client.list_networks()['networks']

        for network in networkslist:
            if network['router:external'] == False and network['tenant_id'] == tenant_id:
                self.delete_network(network['id'],tenant_id)
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

        LOG.debug("Creating ipv6 network")
        net = self.networks_client.create_network(
            **{'name': "Private-ipv6"})
        nets[net['network']['name']] = net['network']['id']
        subnetconfig = {
            'ip_version': 6,
            'network_id': net['network']['id'],
            'name': "IPV6-PS",
            'cidr': 'fdf8:f53b:82e4::53/125'}
        subnet = self.subnets_client.create_subnet(**subnetconfig)
        subnets[subnet['subnet']['name']] = subnet['subnet']['id']
        LOG.debug("Created ipv6 network")

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
            **{'network_id': nets['Private-2'], 'fixed_ips': [{'ip_address': '10.10.2.14'}]})['port']['id']
        self.routers_client.add_router_interface(routers['Router-2'], port_id=portid1)
        portid2 = self.ports_client.create_port(
            **{'network_id': nets['Private-2'], 'fixed_ips': [{'ip_address': '10.10.2.15'}]})['port']['id']
        portid3 = self.ports_client.create_port(
            **{'network_id': nets['Private-2'], 'fixed_ips': [{'ip_address': '10.10.2.16'}]})['port']['id']
        self.routers_client.add_router_interface(routers['Router-4'], port_id=portid2)
        self.routers_client.add_router_interface(routers['Router-5'], port_id=portid3)
        self.routers_client.add_router_interface(routers['Router-4'], subnet_id=subnets['PS-5'])
        portid4 = self.ports_client.create_port(
            **{'network_id': nets['Private-5'], 'fixed_ips': [{'ip_address': '10.10.5.13'}]})['port']['id']
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
        return (networks, subnets, routers, interfaces)

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
        return (snapshot_id, command_execution, snapshot_execution)

    '''
    This method takes restore details as a parameter rest_details. For selective restore key,values of rest_details are : 1. rest_type:selective 2. network_id
    3. subnet_id and 4. instances:{vm_id1:[list of vols associated with it including boot volume if any], vm_id2:[],...}.
    For inplace restore necessary key,values are : 1.rest_type:inplace and 2.instances:{vm_id1:[list of vols associated with it including boot volume if any], vm_id2:[],...}.
    '''

    def create_restore_json(self, rest_details):
        if 'volume_type' not in rest_details.keys():
            rest_details['volume_type'] = CONF.volume.volume_type
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
                            'new_volume_type': rest_details['volume_type']})
                vm_name = "tempest_test_vm_" + instance + "_selectively_restored"
                temp_instance_data = {
                    'id': instance,
                    'availability_zone': CONF.compute.vm_availability_zone,
                    'include': True,
                    'restore_boot_disk': True,
                    'name': vm_name,
                    'vdisks': temp_vdisks_data}
                if 'flavor' in rest_details:
                    LOG.debug("Flavor details set")
                    temp_instance_data['flavor'] = {
                            'vcpus': rest_details['flavor']['vcpus'],
                            'ram': rest_details['flavor']['ram'],
                            'disk': rest_details['flavor']['disk'],
                            'ephemeral': rest_details['flavor']['OS-FLV-EXT-DATA:ephemeral'],
                            'swap': rest_details['flavor']['swap']
                            }
                else:
                    LOG.debug("Flavor details not set")
                instance_details.append(temp_instance_data)
            LOG.debug("Instance details for restore: " + str(instance_details))
            payload = {'instance_details': instance_details,
                       'network_details': network_details}
            return (payload)

        elif rest_details['rest_type'] == 'inplace':
            instances = rest_details['instances']
            instance_details = []
            for instance in instances:
                temp_vdisks_data = []
                for volume in instances[instance]:
                    temp_vdisks_data.append(
                        {
                            'id': volume,
                            'restore_cinder_volume': True,
                            'new_volume_type': rest_details['volume_type']})
                temp_instance_data = {
                    'id': instance,
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
            return (payload)
        elif rest_details['rest_type'] == 'oneclick':
            payload = {
                "openstack": {},
                "type": "openstack",
                "oneclickrestore": True,
                "restore_type": "oneclick"
            }
            return (payload)
        else:
            return

    '''
    This method lists the available types of WLM Quotas
    '''

    def get_quota_type(self):
        resp, body = self.wlm_client.client.get(
            "/project_quota_types")
        LOG.debug("get_quota_type response: %s", resp.content)
        if (resp.status_code != 200):
            resp.raise_for_status()
        quota_types = json.loads(resp.content)
        return quota_types['quota_types']

    '''
    This method returns the quota type id of the specified type
    '''

    def get_quota_type_id(self, quota_type):
        resp, body = self.wlm_client.client.get(
            "/project_quota_types")
        LOG.debug("get_quota_type response: %s", resp.content)
        if (resp.status_code != 200):
            resp.raise_for_status()
        quota_types = (json.loads(resp.content))['quota_types']
        quota_type_id = None
        for q in quota_types:
            if q['display_name'] == quota_type:
                quota_type_id = q['id']
        return quota_type_id

    '''
    This method creates allowed WLM quota for a specific project
    '''

    def create_project_quota(self, project_id, quota_type_id, allowed_value,
                             watermark_value, quota_cleanup=True):
        payload = {"allowed_quotas":
            [{
                "quota_type_id": quota_type_id,
                "project_id": project_id,
                "allowed_value": allowed_value,
                "high_watermark": watermark_value
            }]}
        resp, body = self.wlm_client.client.post(
            "/project_allowed_quotas/" + project_id, json=payload)
        LOG.debug("project-allowed-quota-create response: %s",
                  str(resp.content))
        if resp.status_code != 200:
            resp.raise_for_status()
        quota_resp = (json.loads(resp.content))['allowed_quotas']
        quota_id = None
        for q in quota_resp:
            if (q['quota_type_id'] == quota_type_id and
                    q['project_id'] == project_id):
                quota_id = q['id']
        if (tvaultconf.cleanup and quota_cleanup):
            self.addCleanup(self.delete_project_quota, quota_id)
        return quota_id

    '''
    This method deletes a specified quota
    '''

    def delete_project_quota(self, quota_id):
        resp, body = self.wlm_client.client.delete(
            "/project_allowed_quotas/" + quota_id)
        LOG.debug("project-allowed-quota-delete response: %s",
                  str(resp.content))
        if resp.status_code != 202:
            resp.raise_for_status()
        return True

    '''
    This method updates allowed WLM quota for a specific project
    '''

    def update_project_quota(self, project_id, quota_id, allowed_value,
                             watermark_value):
        payload = {"allowed_quotas":
            {
                "project_id": project_id,
                "allowed_value": allowed_value,
                "high_watermark": watermark_value
            }}
        resp, body = self.wlm_client.client.put(
            "/update_allowed_quota/" + quota_id, json=payload)
        LOG.debug("project-allowed-quota-update response: %s",
                  str(resp.content))
        if resp.status_code != 202:
            resp.raise_for_status()
        quota_resp = (json.loads(resp.content))['allowed_quotas']
        for q in quota_resp:
            if (q['id'] == quota_id and
                    q['allowed_value'] == allowed_value and
                    q['high_watermark'] == watermark_value):
                return True
            else:
                return False

    '''
    This method lists the available quotas set for a specified project
    '''

    def get_quota_list(self, project_id):
        resp, body = self.wlm_client.client.get(
            "/project_allowed_quotas/" + project_id)
        LOG.debug("get_quota_list response: %s", resp.content)
        if resp.status_code != 200:
            resp.raise_for_status()
        quota_list = (json.loads(resp.content))['allowed_quotas']
        return quota_list

    '''
    This method lists the available quotas set for a specified project
    '''

    def get_quota_details(self, quota_id):
        resp, body = self.wlm_client.client.get(
            "/project_allowed_quota/" + quota_id)
        LOG.debug("get_quota_details response: %s", resp.content)
        if resp.status_code != 200:
            resp.raise_for_status()
        quota_resp = (json.loads(resp.content))['allowed_quotas']
        return quota_resp

    '''
    This method returns the quota type id of the specified type using WLM CLI
    '''

    def get_quota_type_id_cli(self, quota_type):
        out = cli_parser.cli_output(
            command_argument_string.quota_type_list)
        quota_types = (json.loads(out))
        quota_type_id = None
        for q in quota_types:
            if q['Name'] == quota_type:
                quota_type_id = q['ID']
                break
        return quota_type_id

    '''
    This method updates the specified workload
    '''

    def workload_modify(self, workload_id, instances, jobschedule={}):
        in_list = []
        for id in instances:
            in_list.append({'instance-id': id})
        if jobschedule != {}:
            payload = {'workload': {'instances': in_list}}
        else:
            payload = {'workload': {'instances': in_list,
                                    'jobschedule': jobschedule}}
        resp, body = self.wlm_client.client.put(
            "/workloads/" + workload_id + "?is_admin_dashboard=False",
            json=payload)
        time.sleep(10)
        if (resp.status_code != 202):
            resp.raise_for_status()
        return True

    """
    This method provides list of rules belonging to a security group
    """

    def list_secgroup_rules_for_secgroupid(self, security_group_id):
        uri = "/security-group-rules?security_group_id=%s" % security_group_id
        resp, body = self.security_group_rules_client.get(self.uri_prefix + uri)
        rules = json.loads(body)
        LOG.debug("Body: {}".format(body))
        LOG.debug("rules_list: {}".format(rules))
        LOG.debug(
            "Check for specifc rules list: {}".format(rules["security_group_rules"])
        )
        rules_list = rules["security_group_rules"]
        return rules_list

    # Delete default security group rules
    def delete_default_rules(self, secgrp_id):
        LOG.debug("Delete default rules from given security group")
        rule_list = self.list_secgroup_rules_for_secgroupid(secgrp_id)
        for each in rule_list:
            self.security_group_rules_client.delete_security_group_rule(each["id"])

    # Compare the security groups by id and fail if verification fails
    def verifySecurityGroupsByID(self, secgrp_id):
        LOG.debug("Compare security groups for: {}".format(secgrp_id))
        flag = False
        try:
            body = self.security_groups_client.list_security_groups()
            security_groups = body["security_groups"]
            print("Secgrp id: {} ".format(secgrp_id))
            for n in security_groups:
                if secgrp_id in n["id"]:
                    LOG.debug(
                        "Security group is present post restore. info: {}".format(
                            n["id"]
                        )
                    )
                    flag = True
            return flag
        except Exception as e:
            LOG.error("Exception in verifySecurityGroupsByID: {}".format(e))
            return False

    # Compare the security groups by name and fail if verification fails
    def verifySecurityGroupsByname(self, secgrp_name):
        LOG.debug("Compare security groups for: {}".format(secgrp_name))
        flag = False
        try:
            body = self.security_groups_client.list_security_groups()
            security_groups = body["security_groups"]
            print("Secgrp name: {} ".format(secgrp_name))
            for n in security_groups:
                if secgrp_name in n["name"]:
                    LOG.debug(
                        "Security group is present post restore. info: {}".format(
                            n["name"]
                        )
                    )
                    flag = True
            return flag
        except Exception as e:
            LOG.error("Exception in verifySecurityGroupsByname: {}".format(e))
            return False

    # Compare the security group & rules assigned to the restored instance and assert if verification fails
    def verifySecurityGroupRules(self, rule_id, secgrp_id, expected_val):
        LOG.debug("Compare security group rules")
        try:
            LOG.debug("Expected val: {}".format(expected_val))
            body = self.security_group_rules_client.show_security_group_rule(rule_id)
            rule = body["security_group_rule"]
            LOG.debug("Each rules: {}".format(rule))
            if rule["protocol"] != None:
                for key, value in expected_val.items():
                    self.assertEqual(
                        value,
                        rule[key],
                        "Field %s of the created security group "
                        "rule does not match with %s." % (key, value),
                    )
            if rule["remote_group_id"] != None:
                LOG.debug("remote group id is present")
                self.assertNotEqual(
                    rule["remote_group_id"],
                    secgrp_id,
                    "remote group id from different security group is not present",
                )
            LOG.debug("Comparison is successful")
            return True
        except AssertionError as e:
            LOG.error("Exception in verifySecurityGroupRules: {}".format(e))
            return False

    # Get the list of restored security policies from restored vms
    def getRestoredSecGroupPolicies(self, restored_vms):
        try:
            restored_secgrps = []
            for vm in restored_vms:
                vmdetails = self.get_vm_details(vm)
                LOG.debug("\nRestored VM details: {}".format(vmdetails))
                server_vm = vmdetails["server"]
                LOG.debug(f"Restored VM details-server: {vmdetails['server']}")
                if 'security_groups' in server_vm.keys():
                    restored_secgrps.extend(server_vm["security_groups"])
            LOG.debug(f"List of restored security groups: {restored_secgrps}")
        except Exception as e:
            LOG.error("Restored instance do not have attached security group")
            LOG.error(f"Exception in getRestoredSecGroupPolicies: {e}")
        finally:
            return restored_secgrps

    def list_security_groups(self, tenant_id=CONF.identity.tenant_id):
        body = self.security_groups_client.list_security_groups(tenant_id=tenant_id)
        security_groups = body["security_groups"]
        LOG.debug("No. of security groups: {}".format(len(security_groups)))
        LOG.debug("List of security groups: {}".format(security_groups))
        return security_groups

    def list_security_group_rules(self, tenant_id=CONF.identity.tenant_id):
        body = self.security_group_rules_client.list_security_group_rules(tenant_id=tenant_id)
        rules_list = body["security_group_rules"]
        LOG.debug("No. of security group rules: {}".format(len(rules_list)))
        LOG.debug("List of security group rules: {}".format(rules_list))
        return rules_list

    # Delete vms, volumes, security groups
    def delete_vm_secgroups(self, vms, secgrp_ids):
        LOG.debug("Delete VM + volume + security groups")
        vol = []
        for vm in vms:
            LOG.debug("Get list of all volumes to be deleted from instance {}".format(vm))
            vol.append(self.get_attached_volumes(vm))
        self.delete_vms([*vms])
        LOG.debug("Delete volumes: {}".format(vol))
        self.delete_volumes(vol)
        for secgrp in secgrp_ids:
            self.delete_security_group(secgrp)
            LOG.debug("Deleted security groups: {}".format(secgrp))


    '''
    This method creates a secret container using secret uuid.
    '''
    def create_secret_container(self, secret_uuid, secret_container_cleanup=True):
        try:
            container_ref = ""
            #get the secret ref using secret_uuid
            response = self.secret_client.get_secret_metadata(secret_uuid)
            secret_data = [
                    {
                        'name' : 'test secret',
                        'secret_ref' : response['secret_ref'] if response else []
                        }
                    ]
            resp = self.container_client.create_container(
                                    type = "generic",
                                    name = "secret-container",
                                    secret_refs = secret_data
                                    )

            #get the container ref
            container_ref = resp['container_ref']

            if (tvaultconf.cleanup and secret_container_cleanup):
                self.addCleanup(self.delete_secret_container, container_ref)

        except Exception as e:
            LOG.error(f"Exception occurred during creation: {e}")
        finally:
            #return the container ref URL
            return container_ref


    '''
    This method deletes a secrete container created
    '''
    def delete_secret_container(self, container_ref):
        try:
            container_uuid = container_ref.split('/')[-1]
            #pass the container uuid to delete the container
            resp = self.container_client.delete_container(container_uuid)
            LOG.debug(f"delete secret container response = {resp}")

        except Exception as e:
            LOG.error(f"Exception occurred during deletion: {e}")
            return False


    '''
    This method creates a secret for workloads
    '''

    def create_secret(self, secret_cleanup=True):
        resp = self.secret_client.create_secret(
            payload=base64.b64encode(b'trilio_test'),
            payload_content_type="text/plain",
            algorithm="aes", mode="cbc",
            bit_length=256,
            secret_type="opaque")
        secret_uuid = resp['secret_ref'].split('/')[-1]
        if (tvaultconf.cleanup and secret_cleanup):
            self.addCleanup(self.delete_secret, secret_uuid)
        return secret_uuid

    '''
    This method deletes a secret
    '''

    def delete_secret(self, secret_uuid):
        resp = self.secret_client.delete_secret(secret_uuid)
        LOG.debug(f"resp {resp}")
        return resp

    '''
    Method to get encryption status of given volume
    '''

    def get_volume_encryption_status(self, volume_id):
        try:
            body = self.volumes_client.show_volume(volume_id)['volume']
            return body['encrypted']
        except lib_exc.NotFound:
            return None

    '''
    Method creates inplace restore for a given snapshot and returns the restore id
    '''

    def snapshot_inplace_restore(
            self,
            workload_id,
            snapshot_id,
            payload={},
            restore_cleanup=True):
        LOG.debug("At the start of snapshot_inplace_restore method")
        LOG.debug(f"Payload: {payload}")
        payload1 = {"restore": {"options": payload}}
        try:
            resp, body = self.wlm_client.client.post(
                "/workloads/" + workload_id + "/snapshots/" + snapshot_id + "/restores", json=payload1)
            restore_id = body['restore']['id']
            LOG.debug(
                "#### workloadid: %s ,snapshot_id: %s , restore_id: %s , operation: snapshot_restore" %
                (workload_id, snapshot_id, restore_id))
            LOG.debug("Response:" + str(resp.content))
            if (resp.status_code != 202):
                resp.raise_for_status()
            LOG.debug('Restore of snapshot %s scheduled succesffuly' %
                      snapshot_id)
            if (tvaultconf.cleanup and restore_cleanup):
                self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
                self.restored_vms = self.get_restored_vm_list(restore_id)
                self.restored_volumes = self.get_restored_volume_list(
                    restore_id)
                self.addCleanup(self.restore_delete,
                                workload_id, snapshot_id, restore_id)
                self.addCleanup(self.delete_restored_vms,
                                self.restored_vms, self.restored_volumes)
        except Exception as e:
            restore_id = 0
            LOG.error(f"Exception in snapshot_inplace_restore: {e}")
        return restore_id

    def attach_interface_to_instance(self, instance_id, network_id):
        try:
            self.interfaces_client.create_interface(
                instance_id, net_id=network_id)
        except Exception as e:
            LOG.error(f"Exception in attach_interface_to_instance: {e}")

    '''
    install qemu-guest-agent package on the instance
    '''

    def install_qemu(self, ssh):
        try:
            buildCommand = "sudo apt install qemu-guest-agent"
            stdin, stdout, stderr = ssh.exec_command(buildCommand)
            time.sleep(20)
        except Exception as e:
            LOG.error("Exception in install_qemu: " + str(e))

    '''
    verify network components post restore
    '''

    def verify_network_restore(self, nt_bf, nt_af, sbnt_bf, sbnt_af, rt_bf,
            rt_af, vm_details_bf, vm_details_af, test_type):
        try:
            if nt_bf == nt_af:
                reporting.add_test_step(
                    "Verify network details after network restore",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify network details after network restore",
                    tvaultconf.FAIL)
                LOG.error(
                    "Network details before and after restore: {0}, {1}".format(
                        nt_bf, nt_af))

            if sbnt_bf == sbnt_af:
                reporting.add_test_step(
                    "Verify subnet details after network restore",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify subnet details after network restore",
                    tvaultconf.FAIL)
                LOG.error(
                    "Subnet details before and after restore: {0}, {1}".format(
                        sbnt_bf, sbnt_af))

            if rt_bf == rt_af:
                reporting.add_test_step(
                    "Verify router details after network restore",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify router details after network restore",
                    tvaultconf.FAIL)
                LOG.error(
                    "Router details before and after restore: {0}, {1}".format(
                        rt_bf, rt_af))

            if test_type.lower() == 'cli':
                if not vm_details_af:
                    reporting.add_test_step("Instances not restored",
                        tvaultconf.PASS)
                else:
                    reporting.add_test_step("Instances are restored",
                        tvaultconf.FAIL)
            else:
                klist = sorted([*vm_details_bf])
                vm_details_bf_sorted = {}
                vm_details_af_sorted = {}

                for vm in klist:
                    netname = [*vm_details_bf[vm]['addresses']]
                    for net in netname:
                        for i in range((len(vm_details_bf[vm]['addresses'][net]))):
                            vm_details_bf[vm]['addresses'][net][i]['OS-EXT-IPS-MAC:mac_addr'] = ''
                            vm_details_af[vm]['addresses'][net][i]['OS-EXT-IPS-MAC:mac_addr'] = ''
                    if 'links' in vm_details_bf[vm].keys() and len(vm_details_bf[vm]['links']) > 1:
                        vm_details_bf[vm]['links'][1]['href'] = ''
                        vm_details_af[vm]['links'][1]['href'] = ''
                    if 'config_drive' in vm_details_af[vm]['metadata']:
                        del vm_details_af[vm]['metadata']['config_drive']
                    if 'ordered_interfaces' in vm_details_af[vm]['metadata']:
                        del vm_details_af[vm]['metadata']['ordered_interfaces']
                    attributes = ['links', 'OS-EXT-SRV-ATTR:host',
                                  'OS-EXT-SRV-ATTR:hypervisor_hostname', 'hostId',
                                  'OS-EXT-SRV-ATTR:instance_name', 'updated',
                                  'created', 'id', 'OS-SRV-USG:launched_at',
                                  'OS-EXT-SRV-ATTR:reservation_id', 'OS-EXT-SRV-ATTR:hostname']
                    for attr in attributes:
                        vm_details_bf[vm][attr] = ''
                        vm_details_af[vm][attr] = ''
                    LOG.debug("VM compare 7")
                    vm_details_af[vm]['name'] = vm_details_af[vm]['name'].replace(
                        'restored_instance', '')
                    vm_details_bf_sorted[vm] = vm_details_bf[vm]
                    vm_details_af_sorted[vm] = vm_details_af[vm]

                if vm_details_bf_sorted == vm_details_af_sorted:
                    reporting.add_test_step(
                        "Verify instance details after restore", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Verify instance details after restore", tvaultconf.FAIL)
                    LOG.error(
                        "Instance details before and after restore: {0}, {1}".format(
                            vm_details_bf, vm_details_af))

        except Exception as e:
            LOG.error("Exception in verify_network_restore: " + str(e))

    '''
    download test image
    '''

    def download_image(self,
            url=tvaultconf.image_url,
            filename=tvaultconf.image_filename):
        try:
            with open(filename, 'wb') as f:
                f.write(requests.get(url+"/"+filename).content)
            return True
        except Exception as e:
            LOG.error("Exception in download_image: " + str(e))
            return False

    '''
    Store image file on glance
    '''

    def upload_image_data(self, image_id, filename=tvaultconf.image_filename):
        try:
            upload_file = self.images_client.store_image_file(
                            image_id, io.open(filename,'rb'))
            LOG.debug(f"upload_file response: {upload_file}")
            return True
        except Exception as e:
            LOG.error("Exception in upload_image_data: " + str(e))
            return False

    '''
    update image properties
    '''

    def update_image(self, image_id, properties=tvaultconf.image_properties):
        try:
            payload = []
            for k,v in properties.items():
                temp = {"op": "add",
                        "path": "/"+str(k),
                        "value": v}
                payload.append(temp)
            self.images_client.update_image(image_id, payload)
            return True
        except Exception as e:
            LOG.error("Exception in update_image: " + str(e))
            return False

    '''
    Create glance image
    '''

    def create_image(self,
            image_name="tempest-test-image",
            image_cleanup=True):
        try:
            if self.download_image():
                image = self.images_client.create_image(
                            disk_format='qcow2',
                            container_format='bare',
                            name=image_name,
                            visibility='public')
                image_id = image['id']
                if (tvaultconf.cleanup and image_cleanup):
                    self.addCleanup(self.delete_image, image_id)
                if self.upload_image_data(image_id):
                    LOG.debug("Image data uploaded")
                else:
                    raise Exception("Image data not uploaded")
                if self.update_image(image_id):
                    LOG.debug("Image properties updated")
                else:
                    raise Exception("Image properties not updated")
                if (tvaultconf.cleanup and image_cleanup):
                    self.addCleanup(self.delete_image, image_id)
                return image_id
            else:
                raise Exception("Image not created in glance")
        except Exception as e:
            LOG.error("Exception in create_image: " + str(e))
            return None

    '''
    Delete glance image
    '''

    def delete_image(self, image_id):
        try:
            image = self.images_client.delete_image(image_id)
            LOG.debug(f"Delete_image response: {image}")
            return True
        except Exception as e:
            LOG.error("Exception in delete_image: " + str(e))
            return False

    '''
    Reboot instance
    '''

    def reboot_instance(self, vm_id):
        try:
            self.servers_client.reboot_server(vm_id, type='SOFT')
        except Exception as e:
            LOG.error("Exception in reboot_instance: " + str(e))

    '''
    List available glance images
    '''

    def list_images(self):
        try:
            images = self.images_client.list_images({'sort':'created_at:desc'})['images']
            LOG.debug(f"List_images response: {images}")
            return images
        except Exception as e:
            LOG.error("Exception in list_images: " + str(e))
            return None

    '''
    Method returns True if snapshot is marked as encrypted on backup target media
    '''

    def check_snapshot_encryption_on_backend(self, mount_path, workload_id,
            snapshot_id, instance_id, disk_name):
        cmd = (tvaultconf.command_prefix).replace("<command>","ls " + \
                str(mount_path).strip() + "/workload_" + \
                str(workload_id).strip() + "/snapshot_" + \
                str(snapshot_id).strip() + "/vm_id_" + \
                str(instance_id).strip())
        p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        match_pattern = "_" + disk_name
        for line in stdout.splitlines():
            if match_pattern in str(line):
                cmd1 = line.decode('utf-8')
                break
        cmd += "/" + cmd1
        p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        cmd2 = stdout.decode('utf-8')

        final_cmd = (tvaultconf.command_prefix).replace("<command>","qemu-img info " + \
                str(mount_path).strip() + "/workload_" + \
                str(workload_id).strip() + "/snapshot_" + \
                str(snapshot_id).strip() + "/vm_id_" + \
                str(instance_id).strip() + "/" + cmd1 + "/" + cmd2)
        p = subprocess.Popen(shlex.split(final_cmd), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        LOG.debug(f"stdout: {stdout}; stderr: {stderr}")
        is_encrypted = False
        for line in stdout.splitlines():
            if str(line).find('encrypted') != -1:
                is_encrypted = True
                break
        return is_encrypted

    '''
    List WLM trusts
    '''

    def get_trusts(self):
        try:
            trust_list = []
            resp, body = self.wlm_client.client.get("/trusts")
            if resp.status_code != 200:
                resp.raise_for_status()
            trust_list = body['trust']
        except Exception as e:
            LOG.error(f"Exception in get_trusts: {e}")
        finally:
            return trust_list

    '''
    Create WLM trust
    '''

    def create_trust(self, role, is_cloud_admin=False, trust_cleanup=False):
        try:
            payload = {"trusts": {"role_name": role,
                                  "is_cloud_trust": is_cloud_admin}
                      }
            resp, body = self.wlm_client.client.post("/trusts", json=payload)
            if resp.status_code != 200:
                resp.raise_for_status()
            trust_id = body['trust'][0]['name']
            if (tvaultconf.cleanup and trust_cleanup):
                self.addCleanup(self.delete_trust, trust_id)
            return trust_id
        except Exception as e:
            LOG.error(f"Exception in create_trust: {e}")
            return None

    '''
    Delete WLM trust
    '''

    def delete_trust(self, trust_id):
        try:
            resp, body = self.wlm_client.client.delete("/trusts/" +
                                str(trust_id))
            if resp.status_code != 200:
                resp.raise_for_status()
            return True
        except Exception as e:
            LOG.error(f"Exception in delete_trust: {e}")
            return False

    '''
    This method creates a secret order 
    '''

    def create_secret_order(self, order_name, order_cleanup=True):
        resp = self.order_client.create_order(
            type="key",
            meta={"name": order_name, "algorithm": "aes", "bit_length": 256, "payload_content_type": "application/octet-stream", "mode": "cbc"}
            )
        order_uuid = resp['order_ref'].split('/')[-1]
        if (tvaultconf.cleanup and order_cleanup):
            self.addCleanup(self.delete_secret_order, order_uuid)
        return order_uuid

    '''
    This method retrieves secret key from secret order
    '''
    def get_secret_from_order(self, order_uuid):
        resp = self.order_client.get_order(order_uuid)
        LOG.debug("response from get secret order: {}".format(resp))
        secret_uuid = resp['secret_ref'].split('/')[-1]
        return secret_uuid

    '''
    This method deletes a secret order
    '''
    def delete_secret_order(self, order_uuid):
        resp = self.order_client.delete_order(order_uuid)
        LOG.debug(f"resp {resp}")
        return resp

    '''
    This method will add additional security groups to instance
    '''
    def add_security_group_to_instance(self, instance_id, sgid):
        try:
            self.servers_client.add_security_group(instance_id, name=sgid)
            LOG.debug("Added security group {} to instance {}".format(sgid, instance_id))
            return True
        except Exception as e:
            LOG.error("Exception in add_security_group_to_instance: {}".format(e))
            return False

    '''
    This method will add get restored security groups for provided name
    '''
    def get_restored_security_group_id_by_name(self, security_group_name):
        security_group_id = ""
        security_groups_list = self.security_groups_client.list_security_groups()[
            'security_groups']
        LOG.debug("Security groups list" + str(security_groups_list))
        for security_group in security_groups_list:
            if security_group['name'] == security_group_name and "Restored from original security group" in security_group['description']:
                security_group_id = security_group['id']
        if security_group_id != "":
            LOG.debug("security group id for security group {}".format(security_group_id))
            return security_group_id
        else:
            LOG.debug("security group id is NOT present/restored")
            return None

    '''
    This method will create new project as required for the test
    '''
    def create_project(self, project_cleanup=True):
        project_name = data_utils.rand_name(name=self.__class__.__name__)
        project = self.projects_client.create_project(
            project_name,
            domain_id=CONF.identity.domain_id)['project']
        LOG.debug("Created project details: {}".format(project))
        project_id = project['id']
        project_details = {"id": project_id, "name": project_name}
        LOG.debug("Created project details: {}".format(project_details))
        if (tvaultconf.cleanup and project_cleanup):
            self.addCleanup(self.delete_project, project['id'])
        return project_details


    '''
    This method will delete the project id passed to it.
    '''
    def delete_project(self, project_id):
        try:
            #delete project id
            resp = self.projects_client.delete_project(project_id)
            LOG.debug(f"Response for project deletion : {resp}")

            return True
        except Exception as e:
            LOG.error(f"Exception in assign_role_to_user_project: {e}")
            return False



    '''
    This method will get the list of triliovault created snapshots
    '''
    def get_trilio_volume_snapshot(self, vol_snap_name):
        trilio_vol_snapshots = []
        vol_snapshots = self.snapshots_extensions_client.list_snapshots()
        LOG.debug("List snapshots: {}".format(vol_snapshots))
        for each in vol_snapshots['snapshots']:
            if (vol_snap_name in each['displayName']):
                trilio_vol_snapshots.append(each)
        LOG.debug("Trilio vault generated cinder snapshots: {}".format(trilio_vol_snapshots))
        return trilio_vol_snapshots

    '''
    Method to list available key pairs
    '''

    def list_key_pairs(self):
        key_pairs_list_response = self.keypairs_client.list_keypairs()
        key_pair_list = key_pairs_list_response['keypairs']
        return key_pair_list

    '''
    Method to get role id for given role name
    '''

    def get_role_id(self, role_name=tvaultconf.test_role):
        role_list = self.roles_client.list_roles()['roles']
        role_id = [role['id'] for role in role_list if role['name'] == \
                role_name]
        LOG.debug(f"Role ID: {role_id}")
        return role_id

    '''
    Method to assign role to given user and project combination
    '''

    def assign_role_to_user_project(self, project_id, user_id, role_id,
            role_cleanup=True):
        try:
            resp = self.roles_client.create_user_role_on_project(
                project_id, user_id, role_id)
            LOG.debug(f"response: {resp}")
            if (tvaultconf.cleanup and role_cleanup):
                self.addCleanup(self.remove_role_from_user_project, project_id,
                        user_id, role_id)
            return True
        except Exception as e:
            LOG.error(f"Exception in assign_role_to_user_project: {e}")
            return False

    '''
    Method to remove role from given user and project combination
    '''

    def remove_role_from_user_project(self, project_id, user_id, role_id):
        try:
            resp = self.roles_client.delete_role_from_user_on_project(
                project_id, user_id, role_id)
            LOG.debug(f"response: {resp}")
            return True
        except Exception as e:
            LOG.error(f"Exception in remove_role_from_user_project: {e}")
            return False

    '''
    Method to get db data for workload validations - DB cleanup
    '''
    def db_cleanup_workload_validations(self, workload_id):
        workload_validations = {}
        LOG.debug("Getting list for db cleanup workload validations: {}".format(workload_id))

        workload_tables = tvaultconf.workload_tables
        LOG.debug("Print workload_tables: {}".format(workload_tables))
        for each in workload_tables:
            if (each == "workload_vm_metadata"):
                # Below code will fetch count from workload_vms_metadata table based on join query
                count = query_data.get_workload_vm_data(workload_id)
            elif (each == "workloads"):
                count = query_data.get_db_rows_count(each, "id", workload_id)
            else:
                count = query_data.get_db_rows_count(each, "workload_id", workload_id)
            LOG.debug("Count for {} is: {}".format(each, count))
            workload_validations[each] = count

        LOG.debug("DB counts for workload validations: {}".format(workload_validations))
        return workload_validations

    '''
    Method to get db data for snapshot validations - DB cleanup
    '''
    def db_cleanup_snapshot_validations(self, snapshot_id):
        snapshot_validations = {}
        LOG.debug("Getting list for db cleanup snapshot validations.")

        snapshot_tables = tvaultconf.snapshot_tables
        LOG.debug("Print snapshot_tables: {}".format(snapshot_tables))
        for each in snapshot_tables:
            if (each == "snapshots"):
                count = query_data.get_db_rows_count(each, "id", snapshot_id)
            elif (each == "snapshot_vm_metadata"):
                count = query_data.get_snapshot_vm_data(snapshot_id)
            elif (each == "vm_disk_resource_snaps"):
                count = query_data.get_vm_disk_resource_snaps(snapshot_id)
            elif (each == "vm_disk_resource_snap_metadata"):
                count = query_data.get_vm_disk_resource_snaps_metadata(snapshot_id)
            elif (each == "vm_network_resource_snaps"):
                count = query_data.get_vm_network_resource_snaps(snapshot_id)
            elif (each == "vm_network_resource_snap_metadata"):
                count = query_data.get_vm_network_resource_snaps_metadata(snapshot_id)
            elif (each == "snap_network_resource_metadata"):
                count = query_data.get_snap_network_resource_metadata(snapshot_id)
            else:
                count = query_data.get_db_rows_count(each, "snapshot_id", snapshot_id)
            LOG.debug("Count for {} is: {}".format(each, count))
            snapshot_validations[each] = count

        LOG.debug("DB counts for snapshot validations: {}".format(snapshot_validations))
        return snapshot_validations

    '''
    Method to get db data for restore validations - DB cleanup
    '''
    def db_cleanup_restore_validations(self, restore_id):
        restore_validations = {}
        LOG.debug("Getting list for db cleanup restore validations.")

        restore_tables = tvaultconf.restore_tables
        LOG.debug("Print restore_tables: {}".format(restore_tables))
        for each in restore_tables:
            if (each == "restores"):
                count = query_data.get_db_rows_count(each, "id", restore_id)
            elif (each == "restored_vm_metadata"):
                count = query_data.get_restored_vm_metadata(restore_id)
            elif (each == "restored_vm_resource_metadata"):
                count = query_data.get_restored_vm_resource_metadata(restore_id)
            else:
                count = query_data.get_db_rows_count(each, "restore_id", restore_id)
            LOG.debug("Count for {} is: {}".format(each, count))
            restore_validations[each] = count

        LOG.debug("DB counts for restore validations: {}".format(restore_validations))
        return restore_validations

    '''
    Method to get db data for workload policy validations - DB cleanup
    '''
    def db_cleanup_workload_policy_validations(self, workload_policy_id):
        workload_policy_validations = {}
        LOG.debug("Getting list for db cleanup workload validations: {}".format(workload_policy_id))

        workload_policy_tables = tvaultconf.workload_policy_tables
        LOG.debug("Print workload_policy_tables: {}".format(workload_policy_tables))
        for each in workload_policy_tables:
            if (each == "workload_policy"):
                count = query_data.get_db_rows_count(each, "id", workload_policy_id)
            else:
                count = query_data.get_db_rows_count(each, "policy_id", workload_policy_id)
            LOG.debug("Count for {} is: {}".format(each, count))
            workload_policy_validations[each] = count

        LOG.debug("DB counts for workload validations: {}".format(workload_policy_validations))
        return workload_policy_validations

    '''
    Method returns True if workload dir exists on backup target media
    '''

    def check_workload_exist_on_backend(self, mount_path, workload_id):
        cmd = (tvaultconf.command_prefix).replace("<command>","ls " + str(mount_path).strip() +\
                "/workload_" + str(workload_id).strip())
        p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        LOG.debug(f"stdout: {stdout}; stderr: {stderr}")
        if str(stderr).find('No such file or directory') != -1:
            return False
        else:
            return True


    '''
    Method to create user
    '''
    def createUser(self, user_cleanup=True):
        try:
            # Create a user.
            u_name = data_utils.rand_name('user')
            u_desc = u_name + 'description'
            u_email = u_name + '@testmail.tm'
            u_password = data_utils.rand_password()
            user_body = self.users_client.create_user(
                name=u_name, description=u_desc, password=u_password,
                email=u_email, enabled=True)['user']

            LOG.debug(f"createUser response is : {user_body['id']} and user name is {user_body['name']}")

            #add cleanup
            if (tvaultconf.cleanup and user_cleanup):
                self.addCleanup(self.deleteUser, user_body['id'])

            return user_body

        except Exception as e:
            LOG.error(f"Exception in create_user : {e}")
            return False



    '''
    Method to delete  user
    '''
    def deleteUser(self, user_id):
        try:
            #delete a user
            resp = self.users_client.delete_user(user_id)
            LOG.debug(f"response in delete_user : {resp}")
            return True

        except Exception as e:
            LOG.error(f"Exception in delete_user : {e}")
            return False

    '''
    Method to execute curl command on instance
    '''

    def executecurlonvm(self, ssh, command):
        stdin, stdout, stderr = ssh.exec_command("curl " + command)
        time.sleep(15)
        output = stdout.readlines()
        LOG.debug("command executed: " + str(output))
        return output

    '''
    Method returns True if snapshot dir is exists on backup target media
    '''

    def check_snapshot_size_on_backend(self, mount_path, workload_id,
            snapshot_id, instance_id, disk_name="vda"):
        snapshot_size = 0
        cmd = (tvaultconf.command_prefix).replace("<command>","ls " + \
                str(mount_path).strip() + "/workload_" + \
                str(workload_id).strip() + "/snapshot_" + \
                str(snapshot_id).strip() + "/vm_id_" + \
                str(instance_id).strip())

        LOG.debug("Command to get vdisks: {}".format(cmd))
        p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        match_pattern = "_" + disk_name
        for line in stdout.splitlines():
            if match_pattern in str(line):
                cmd1 = line.decode('utf-8')
                break
        cmd += "/" + cmd1
        p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        cmd2 = stdout.decode('utf-8')

        # block size calculation is done for MB: 1 MB = 1048576 bytes
        final_cmd = (tvaultconf.command_prefix).replace("<command>","ls -s --block-size=1048576 " + \
                str(mount_path).strip() + "/workload_" + \
                str(workload_id).strip() + "/snapshot_" + \
                str(snapshot_id).strip() + "/vm_id_" + \
                str(instance_id).strip() + "/" + cmd1 + "/" + cmd2)
        LOG.debug(f"Final command for snapshot size in MB: {final_cmd}")
        p = subprocess.Popen(shlex.split(final_cmd), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        LOG.debug(f"stdout: {stdout}; stderr: {stderr}")
        if str(stderr).find('No such file or directory') != -1:
            return snapshot_size
        else:
            snapshot_size = str(stdout.decode("utf-8")).split(' ')[0]
            return snapshot_size

