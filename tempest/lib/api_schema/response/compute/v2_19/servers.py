# Copyright 2016 NEC Corporation.  All rights reserved.
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

import copy

from tempest.lib.api_schema.response.compute.v2_16 import servers \
    as serversv216

# Compute microversion 2.19:
# 1. New attributes in 'server' dict.
#      'description'
get_server = copy.deepcopy(serversv216.get_server)
get_server['response_body']['properties']['server'][
    'properties'].update({'description': {'type': ['string', 'null']}})
get_server['response_body']['properties']['server'][
    'required'].append('description')

list_servers_detail = copy.deepcopy(serversv216.list_servers_detail)
list_servers_detail['response_body']['properties']['servers']['items'][
    'properties'].update({'description': {'type': ['string', 'null']}})
list_servers_detail['response_body']['properties']['servers']['items'][
    'required'].append('description')

update_server = copy.deepcopy(serversv216.update_server)
update_server['response_body']['properties']['server'][
    'properties'].update({'description': {'type': ['string', 'null']}})
update_server['response_body']['properties']['server'][
    'required'].append('description')

rebuild_server = copy.deepcopy(serversv216.rebuild_server)
rebuild_server['response_body']['properties']['server'][
    'properties'].update({'description': {'type': ['string', 'null']}})
rebuild_server['response_body']['properties']['server'][
    'required'].append('description')

rebuild_server_with_admin_pass = copy.deepcopy(
    serversv216.rebuild_server_with_admin_pass)
rebuild_server_with_admin_pass['response_body']['properties']['server'][
    'properties'].update({'description': {'type': ['string', 'null']}})
rebuild_server_with_admin_pass['response_body']['properties']['server'][
    'required'].append('description')

# NOTE(gmann): Below are the unchanged schema in this microversion. We need
# to keep this schema in this file to have the generic way to select the
# right schema based on self.schema_versions_info mapping in service client.
# ****** Schemas unchanged since microversion 2.16 ******
list_servers = copy.deepcopy(serversv216.list_servers)
show_server_diagnostics = copy.deepcopy(serversv216.show_server_diagnostics)
get_remote_consoles = copy.deepcopy(serversv216.get_remote_consoles)
attach_volume = copy.deepcopy(serversv216.attach_volume)
show_volume_attachment = copy.deepcopy(serversv216.show_volume_attachment)
list_volume_attachments = copy.deepcopy(serversv216.list_volume_attachments)
