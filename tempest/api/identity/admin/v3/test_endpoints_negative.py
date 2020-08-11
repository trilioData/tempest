# Copyright 2013 IBM Corp.
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

from tempest.api.identity import base
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc


class EndpointsNegativeTestJSON(base.BaseIdentityV3AdminTest):
    # NOTE: force_tenant_isolation is true in the base class by default but
    # overridden to false here to allow test execution for clouds using the
    # pre-provisioned credentials provider.
    force_tenant_isolation = False

    @classmethod
    def setup_clients(cls):
        super(EndpointsNegativeTestJSON, cls).setup_clients()
        cls.client = cls.endpoints_client

    @classmethod
    def resource_setup(cls):
        super(EndpointsNegativeTestJSON, cls).resource_setup()
        s_name = data_utils.rand_name('service')
        s_type = data_utils.rand_name('type')
        s_description = data_utils.rand_name('description')
        service_data = (
            cls.services_client.create_service(name=s_name, type=s_type,
                                               description=s_description)
            ['service'])
        cls.addClassResourceCleanup(cls.services_client.delete_service,
                                    service_data['id'])

        cls.service_id = service_data['id']

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('ac6c137e-4d3d-448f-8c83-4f13d0942651')
    def test_create_with_enabled_False(self):
        # Enabled should be a boolean, not a string like 'False'
        interface = 'public'
        url = data_utils.rand_url()
        region = data_utils.rand_name('region')
        self.assertRaises(lib_exc.BadRequest, self.client.create_endpoint,
                          service_id=self.service_id, interface=interface,
                          url=url, region=region, enabled='False')

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('9c43181e-0627-484a-8c79-923e8a59598b')
    def test_create_with_enabled_True(self):
        # Enabled should be a boolean, not a string like 'True'
        interface = 'public'
        url = data_utils.rand_url()
        region = data_utils.rand_name('region')
        self.assertRaises(lib_exc.BadRequest, self.client.create_endpoint,
                          service_id=self.service_id, interface=interface,
                          url=url, region=region, enabled='True')

    def _assert_update_raises_bad_request(self, enabled):

        # Create an endpoint
        region1_name = data_utils.rand_name('region')
        url1 = data_utils.rand_url()
        interface1 = 'public'
        endpoint_for_update = (
            self.client.create_endpoint(service_id=self.service_id,
                                        interface=interface1,
                                        url=url1, region=region1_name,
                                        enabled=True)['endpoint'])
        region1 = self.regions_client.show_region(region1_name)['region']
        self.addCleanup(self.regions_client.delete_region, region1['id'])
        self.addCleanup(self.client.delete_endpoint, endpoint_for_update['id'])

        self.assertRaises(lib_exc.BadRequest, self.client.update_endpoint,
                          endpoint_for_update['id'], enabled=enabled)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('65e41f32-5eb7-498f-a92a-a6ccacf7439a')
    def test_update_with_enabled_False(self):
        # Enabled should be a boolean, not a string like 'False'
        self._assert_update_raises_bad_request('False')

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('faba3587-f066-4757-a48e-b4a3f01803bb')
    def test_update_with_enabled_True(self):
        # Enabled should be a boolean, not a string like 'True'
        self._assert_update_raises_bad_request('True')
