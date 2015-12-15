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
from testtools import testcase
from tempest import api
import sys
from tempest.common import compute
import time
from tempest.common import waiters
from oslo_config import cfg

CONF = config.CONF
LOG = logging.getLogger(__name__)


class BaseWorkloadmgrTest(tempest.test.BaseTestCase):

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

    @classmethod
    def getWorkloadStatus(self, workload_id):
        resp, body =self.client.client.get("/workloads/"+workload_id)
        workload_status = body['workload']['status']
        LOG.debug("#### workloadid: %s , operation:show_workload" % workload_id)
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
           resp.raise_for_status()
        return workload_status

    @classmethod
    def getSnapshotStatus(cls, workload_id, snapshot_id):
        resp, body = cls.client.client.get("/workloads/"+workload_id+"/snapshots/"+snapshot_id)
        snapshot_status = body['snapshot']['status']
        LOG.debug("#### workloadid: %s ,snapshot_id: %s , operation:show_snapshot" % (workload_id, snapshot_id))
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
           resp.raise_for_status()
        return snapshot_status

    @classmethod
    def getRestoreStatus(cls, workload_id, snapshot_id, restore_id):
        resp, body = cls.client.client.get("/workloads/"+workload_id+"/snapshots/"+snapshot_id+"/restores/"+restore_id)
        restore_status = body['restore']['status']
        LOG.debug("#### workloadid: %s ,snapshot_id: %s, restore_id: %s, operation: show_restore" % (workload_id, snapshot_id, restore_id))
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
           resp.raise_for_status()
        return restore_status

    @classmethod
    def create_vm(cls):
        server=cls.servers_client.create_server(name="tempest-test-vm-1", imageRef=CONF.compute.image_ref, flavorRef=CONF.compute.flavor_ref)
        server_id= server['server']['id']
        waiters.wait_for_server_status(cls.servers_client, server_id, status='ACTIVE')
        return server_id

    @classmethod
    def create_vms(cls, totalVms):
        instances = []
        for vm in range(0,totalVms):
            server=cls.servers_client.create_server(name="tempest-test-vm-1", imageRef=CONF.compute.image_ref, flavorRef=CONF.compute.flavor_ref)
            instances.append(server['server']['id'])
            waiters.wait_for_server_status(cls.servers_client, server['server']['id'], status='ACTIVE')
            
        return instances


    @classmethod
    def delete_vm(cls, server_id=None):
        cls.servers_client.delete_server(server_id)
        waiters.wait_for_server_termination(cls.servers_client, server_id)

    @classmethod
    def delete_vms(cls, instances):
        totalVms = len(instances)
        for vm in range(0,totalVms):
            cls.servers_client.delete_server(instances[vm])
            waiters.wait_for_server_termination(cls.servers_client, instances[vm])
        LOG.debug('DeletedVms: %s' % instances)


    @classmethod
    def create_volume(cls, size=1, volume_type_id=None):
        volume = cls.volumes_client.create_volume(size=size, volume_type=volume_type_id)
        volume_id= volume['volume']['id']
        waiters.wait_for_volume_status(cls.volumes_client,
                                       volume_id, 'available')
        return volume_id

    @classmethod
    def delete_volume(cls, volume_id):
        cls.volumes_client.delete_volume(volume_id)
       

    @classmethod
    def attach_volume(cls, volume_id, server_id, device):
        cls.volumes_client.attach_volume(volume_id,
                                  server_id,
                                  device)
        waiters.wait_for_volume_status(cls.volumes_client,
                                       volume_id, 'in-use')

    @classmethod
    def detach_volume(cls, volume_id):
        cls.volumes_client.detach_volume(volume_id)
        waiters.wait_for_volume_status(cls.volumes_client,
                                       volume_id, 'available')


    @classmethod
    def workload_create(cls, instances, workload_type):
        in_list = []
        for id in instances:
            in_list.append({'instance-id':id})
        payload={'workload': {'name': 'tempest-test-workload',
                              'workload_type_id': workload_type,
                              'source_platform': 'openstack',
                              'instances': in_list,
                              'jobschedule': {},
                              'metadata': {},
                              'description': 'test'}}
        resp, body = cls.wlm_client.client.post("/workloads", json=payload)
        workload_id = body['workload']['id']
        LOG.debug("#### workloadid: %s , operation:workload_create" % workload_id)
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 202):
            resp.raise_for_status()
        LOG.debug('WorkloadCreated: %s' % workload_id)
        return workload_id


    @classmethod
    def workload_delete(cls, workload_id):
        resp, body = cls.wlm_client.client.delete("/workloads/"+workload_id)
        LOG.debug("#### workloadid: %s , operation: workload_delete" % workload_id)
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 202):
            resp.raise_for_status()
        LOG.debug('WorkloadDeleted: %s' % workload_id)

    @classmethod
    def workload_snapshot(cls, workload_id, is_full):
        payload={'snapshot': { 'name': 'Tempest-test-snapshot',
                               'description': 'Test',
                               'full': 'True'}}
        #cls.wait_for_workload_tobe_available(workload_id)
        resp, body = cls.wlm_client.client.post("/workloads/"+workload_id,json=payload)
        snapshot_id = body['snapshot']['id']
        LOG.debug("#### workloadid: %s ,snapshot_id: %s , operation: workload_snapshot" % (workload_id, snapshot_id))
        LOG.debug("Response:"+ str(resp.content))
        #cls.wait_for_workload_tobe_available(workload_id)
        return snapshot_id

    @classmethod
    def wait_for_workload_tobe_available(cls, workload_id):
        status = "available"
        start_time = int(time.time())
        LOG.debug('Checking workload status')
        while ( status != cls.getWorkloadStatus(workload_id)):
            LOG.debug('workload status is: %s , sleeping for a minute' % cls.getWorkloadStatus(workload_id))
            time.sleep(180)
        LOG.debug('workload status of workload %s: %s' % (workload_id, cls.getWorkloadStatus(workload_id)))

    @classmethod
    def is_snapshot_successful(cls, workload_id, snapshot_id):
        is_successful= "False"
        if(cls.getSnapshotStatus(workload_id, snapshot_id) == 'available'):
            LOG.debug('snapshot successful: %s' % snapshot_id)
            is_successful = "True"
        return is_successful


    @classmethod
    def snapshot_delete(cls, workload_id, snapshot_id):
        cls.wait_for_workload_tobe_available(workload_id)
        resp, body = cls.wlm_client.client.delete("/workloads/"+workload_id+"/snapshots/"+snapshot_id)
        LOG.debug("#### workloadid: %s ,snapshot_id: %s  , Operation: snapshot_delete" % (workload_id, snapshot_id))
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 202):
            resp.raise_for_status()
        cls.wait_for_workload_tobe_available(workload_id)
        LOG.debug('SnapshotDeleted: %s' % workload_id)


    @classmethod
    def snapshot_restore(cls, workload_id, snapshot_id):
        LOG.debug("At the start of snapshot_restore method")
        payload={"restore": {"options": {"description": "Tempest test restore",
                                           "oneclickrestore": False,
                                           "vmware": {},
                                           "openstack": {"instances": [], "zone": ""},
                                           "type": "openstack",
                                           "restore_options": {},
                                           "name": "Tempest test restore"},
                "name": "Tempest test restore",
                "description": "Tempest test restore"}}
        LOG.debug("In snapshot_restore method, before calling waitforsnapshot method")
        cls.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
        LOG.debug("After returning from waitfor snapshot")
        resp, body = cls.wlm_client.client.post("/workloads/"+workload_id+"/snapshots/"+snapshot_id+"/restores",json=payload)
        restore_id = body['restore']['id']
        LOG.debug("#### workloadid: %s ,snapshot_id: %s , restore_id: %s , operation: snapshot_restore" % (workload_id, snapshot_id, restore_id))
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 202):
            resp.raise_for_status()
        LOG.debug('Restore of snapshot %s scheduled succesffuly' % snapshot_id)
        cls.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
        return restore_id


    @classmethod
    def wait_for_snapshot_tobe_available(cls, workload_id, snapshot_id):
        status = "available"
        start_time = int(time.time())
        LOG.debug('Checking snapshot status')
        while ( status != cls.getSnapshotStatus(workload_id, snapshot_id)):
            LOG.debug('Snapshot status is: %s' % cls.getSnapshotStatus(workload_id, snapshot_id))
            time.sleep(60)
        LOG.debug('Status of snapshot %s : %s' % snapshot_id, cls.getSnapshotStatus(workload_id, snapshot_id))


    @classmethod
    def is_restore_successful(cls, workload_id, snapshot_id, restore_id):
        is_successful= "False"
        if(cls.getRestoreStatus(workload_id, snapshot_id, restore_id) == 'available'):
            is_successful = "True"
        return is_successful

        
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
