# Copyright 2016 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from tempest.lib.services.identity.v3 import endpoints_client
from tempest.tests.lib import fake_auth_provider
from tempest.tests.lib.services import base


class TestEndpointsClient(base.BaseServiceTest):
    FAKE_CREATE_ENDPOINT = {
        "endpoint": {
            "id": 1,
            "tenantId": 1,
            "region": "North",
            "type": "compute",
            "publicURL": "https://compute.north.public.com/v1",
            "internalURL": "https://compute.north.internal.com/v1",
            "adminURL": "https://compute.north.internal.com/v1"
        }
    }

    FAKE_LIST_ENDPOINTS = {
        "endpoints": [
            {
                "id": 1,
                "tenantId": "1",
                "region": "North",
                "type": "compute",
                "publicURL": "https://compute.north.public.com/v1",
                "internalURL": "https://compute.north.internal.com/v1",
                "adminURL": "https://compute.north.internal.com/v1"
            },
            {
                "id": 2,
                "tenantId": "1",
                "region": "South",
                "type": "compute",
                "publicURL": "https://compute.north.public.com/v1",
                "internalURL": "https://compute.north.internal.com/v1",
                "adminURL": "https://compute.north.internal.com/v1"
            }
        ]
    }

    FAKE_SERVICE_ID = "a4dc5060-f757-4662-b658-edd2aefbb41d"

    def setUp(self):
        super(TestEndpointsClient, self).setUp()
        fake_auth = fake_auth_provider.FakeAuthProvider()
        self.client = endpoints_client.EndPointsClient(fake_auth,
                                                       'identity', 'regionOne')

    def _test_create_endpoint(self, bytes_body=False):
        self.check_service_client_function(
            self.client.create_endpoint,
            'tempest.lib.common.rest_client.RestClient.post',
            self.FAKE_CREATE_ENDPOINT,
            bytes_body,
            status=201,
            service_id="b344506af7644f6794d9cb316600b020",
            region="region-demo",
            publicurl="https://compute.north.public.com/v1",
            adminurl="https://compute.north.internal.com/v1",
            internalurl="https://compute.north.internal.com/v1")

    def _test_list_endpoints(self, bytes_body=False, mock_args='endpoints',
                             **params):
        self.check_service_client_function(
            self.client.list_endpoints,
            'tempest.lib.common.rest_client.RestClient.get',
            self.FAKE_LIST_ENDPOINTS,
            bytes_body,
            mock_args=[mock_args],
            **params)

    def test_create_endpoint_with_str_body(self):
        self._test_create_endpoint()

    def test_create_endpoint_with_bytes_body(self):
        self._test_create_endpoint(bytes_body=True)

    def test_list_endpoints_with_str_body(self):
        self._test_list_endpoints()

    def test_list_endpoints_with_bytes_body(self):
        self._test_list_endpoints(bytes_body=True)

    def test_list_endpoints_with_params(self):
        # Run the test separately for each param, to avoid assertion error
        # resulting from randomized params order.
        mock_args = 'endpoints?service_id=%s' % self.FAKE_SERVICE_ID
        self._test_list_endpoints(mock_args=mock_args,
                                  service_id=self.FAKE_SERVICE_ID)

        mock_args = 'endpoints?interface=public'
        self._test_list_endpoints(mock_args=mock_args, interface='public')

    def test_delete_endpoint(self):
        self.check_service_client_function(
            self.client.delete_endpoint,
            'tempest.lib.common.rest_client.RestClient.delete',
            {},
            endpoint_id="b344506af7644f6794d9cb316600b020",
            status=204)
