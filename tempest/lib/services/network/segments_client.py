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

from tempest.lib.services.network import base


class SegmentsClient(base.BaseNetworkClient):

    def create_segment(self, **kwargs):
        """Creates a segment.

        For a full list of available parameters, please refer to the official
        API reference:
        https://docs.openstack.org/api-ref/network/v2/index.html#create-segment
        """
        uri = '/segments'
        post_data = {'segment': kwargs}
        return self.create_resource(uri, post_data)

    def update_segment(self, segment_id, **kwargs):
        """Updates a segment.

        For a full list of available parameters, please refer to the official
        API reference:
        https://docs.openstack.org/api-ref/network/v2/index.html#update-segment
        """
        uri = '/segments/%s' % segment_id
        post_data = {'segment': kwargs}
        return self.update_resource(uri, post_data)

    def show_segment(self, segment_id, **fields):
        """Shows details of a segment.

        For a full list of available parameters, please refer to the official
        API reference:
        https://docs.openstack.org/api-ref/network/v2/index.html#show-segment-details
        """
        uri = '/segments/%s' % segment_id
        return self.show_resource(uri, **fields)

    def delete_segment(self, segment_id):
        """Deletes a segment"""
        uri = '/segments/%s' % segment_id
        return self.delete_resource(uri)

    def list_segments(self, **filters):
        """Lists segments.

        For a full list of available parameters, please refer to the official
        API reference:
        https://docs.openstack.org/api-ref/network/v2/index.html#list-segments
        """
        uri = '/segments'
        return self.list_resources(uri, **filters)
