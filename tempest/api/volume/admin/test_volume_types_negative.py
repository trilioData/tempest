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

from tempest.api.volume import base
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc


class VolumeTypesNegativeTest(base.BaseVolumeAdminTest):

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('878b4e57-faa2-4659-b0d1-ce740a06ae81')
    def test_create_with_empty_name(self):
        # Should not be able to create volume type with an empty name.
        self.assertRaises(
            lib_exc.BadRequest,
            self.admin_volume_types_client.create_volume_type, name='')

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('994610d6-0476-4018-a644-a2602ef5d4aa')
    def test_get_nonexistent_type_id(self):
        # Should not be able to get volume type with nonexistent type id.
        self.assertRaises(lib_exc.NotFound,
                          self.admin_volume_types_client.show_volume_type,
                          data_utils.rand_uuid())

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('6b3926d2-7d73-4896-bc3d-e42dfd11a9f6')
    def test_delete_nonexistent_type_id(self):
        # Should not be able to delete volume type with nonexistent type id.
        self.assertRaises(lib_exc.NotFound,
                          self.admin_volume_types_client.delete_volume_type,
                          data_utils.rand_uuid())

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('8c09f849-f225-4d78-ba87-bffd9a5e0c6f')
    def test_create_volume_with_private_volume_type(self):
        # Should not be able to create volume with private volume type.
        params = {'os-volume-type-access:is_public': False}
        volume_type = self.create_volume_type(**params)
        self.assertRaises(lib_exc.NotFound,
                          self.create_volume, volume_type=volume_type['id'])
