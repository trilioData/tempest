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

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        cls.client = cls.os.wlm_client

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_list_workloads(self):
        resp, body = self.client.client.get("/workloads")
        data = body['workloads']
        self.assertEqual(200, resp.status_code)
        self.assertNotEmpty(data, "No workloads found")
   
    @test.attr(type='smoke')
    @test.idempotent_id('98337da7-e7f1-43dc-b214-f295a6cb38d6')
    def test_create_workload(self):
        server_client=self.servers_client
        server=server_client.create_server(name="tempest-test-vm-1", imageRef=CONF.compute.image_ref, flavorRef=CONF.compute.flavor_ref)
        id1= server['server']['id']
        server=server_client.create_server(name="tempest-test-vm-1", imageRef=CONF.compute.image_ref, flavorRef=CONF.compute.flavor_ref)
        id2= server['server']['id']
        instances=[id1,id2]
        in_list = []
        for id in instances:
            in_list.append({'instance-id':id})
        payload={'workload': {  'name': 'test2',
                'workload_type_id': '2ddd528d-c9b4-4d7e-8722-cc395140255a',
                'source_platform': 'Openstack',
                'instances': in_list,
                'jobschedule': {},
                'metadata': {},
                'description': 'test'}}
        LOG.debug('JsonPayload: %s' % payload)
        #payload={"workload": {"name": "test2", "workload_type_id": "2ddd528d-c9b4-4d7e-8722-cc395140255a", "source_platform": "Openstack", "instances": [{"instance-id":id}], "jobschedule": {}, "metadata": {}, "description": "test"}}
        #payload_json = json.dumps(payload)
        print("New VMs info"+ str(id))
        resp, body = self.client.client.post("/workloads", json=payload)
        self.assertEqual(202, resp.status_code)


    @test.attr(type='smoke')
    @test.idempotent_id('e7198cb2-9445-4d8d-89ba-d15e43cf5372')
    def test_delete_workload(self):
        server_client=self.servers_client
        server=server_client.create_server(name="tempest-test-vm-1", imageRef=CONF.compute.image_ref, flavorRef=CONF.compute.flavor_ref)
        id= server['server']['id']
        payload_python={"workload": {"name": "test2", "workload_type_id": "2ddd528d-c9b4-4d7e-8722-cc395140255a", "source_platform": "Openstack", "instances": [{"instance-id": id }], "jobschedule": {}, "metadata": {}, "description": "test"}}
        payload=payload_python.dumps()
        LOG.debug('Json payload:%s' % payload)
        resp, body = self.client.client.post("/workloads", json=payload)
        self.assertEqual(202, resp.status_code)
        workload_id = body['workload']['id']
        resp, body = self.client.client.delete("/workloads/"+workload_id)
        self.assertEqual(202, resp.status_code)

          


    @test.attr(type='smoke')
    @test.idempotent_id('f4a2d4c7-9e9f-4ac0-8230-3d168987c5d2')
    def test_apis(self):
        instances = self.create_vms(1)
        workload_id=self.workload_create(instances,'2ddd528d-c9b4-4d7e-8722-cc395140255a')
        snapshot_id=self.workload_snapshot(workload_id,"True")
        self.wait_for_workload_tobe_available(workload_id)
#        if (self.is_snapshot_successful(workload_id,snapshot_id)):
#            LOG.debug("Snapshot successful")
#            self.snapshot_restore(workload_id, snapshot_id)
#            if (self.is_restore_successful(workload_id,snapshot_id, restore_id)):
#                LOG.debug("restore successful")
#            else:
#                LOG.debug("restore failed") 
#        else:
#            LOG.debug("Snapshot Failed")
#        
#        self.snapshot_delete(workload_id, snapshot_id)
#        workload_status=self.getWorkloadStatus(workload_id)
#        #self.wait_for_workload_tobe_available(workload_id,"available") 
#        LOG.debug('Workload status of %s before deletion %s' % (workload_id, workload_status))  
#      
#        self.workload_delete(workload_id)
#        self.delete_vms(instances)


    @test.attr(type='smoke')
    @test.idempotent_id('da638914-8a66-4e98-9fdc-e233b16723dc')
    def test_volume(self):
        server_client=self.servers_client
        server=server_client.create_server(name="tempest-test-vm-1", imageRef=CONF.compute.image_ref, flavorRef=CONF.compute.flavor_ref)
        server_id= server['server']['id']
        waiters.wait_for_server_status(server_client, server_id, 'ACTIVE')
        volumes_client = self.volumes_extensions_client
        device = '/dev/vdc'
        volume = volumes_client.create_volume(size=1, volume_type=tvaultconf.volume_type_ceph)
        waiters.wait_for_volume_status(volumes_client,
                                       volume['volume']['id'], 'available')
        server_client.attach_volume(server_id,
                                  volumeId=volume['volume']['id'],
                                  device=device)
        waiters.wait_for_volume_status(volumes_client,
                                       volume['volume']['id'], 'in-use')
