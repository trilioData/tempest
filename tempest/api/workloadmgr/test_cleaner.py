from tempest.util import query_data
from tempest.util import cli_parser
from tempest import command_argument_string
import time
from tempest import reporting
from tempest import tvaultconf
from oslo_log import log as logging
from tempest.lib import decorators
from tempest import config
from tempest.api.workloadmgr import base
import sys
import os
import json
sys.path.append(os.getcwd())

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    def delete_restores(self):
        restores = [restore for restore in self.wlm_client.restores.list()]
        for restore in restores:
            try:
                self.wlm_client.restores.delete(restore.id)
                self.wait_for_workload_tobe_available(restore.workload_id)
            except BaseException:
                pass

    def delete_snapshots(self):
        snapshots = [snapshot for snapshot in self.wlm_client.snapshots.list()]
        for snapshot in snapshots:
            try:
                self.wlm_client.snapshots.delete(snapshot.id)
                self.wait_for_snapshot_tobe_available(
                    snapshot.workload_id, snapshot.id)
            except BaseException:
                pass

    def delete_workloads(self):
        wls = [wl.id for wl in self.wlm_client.workloads.list()]
        for wl in wls:
            try:
                self.wlm_client.workloads.delete(wl)
                self.wait_for_workload_tobe_available(wl)
            except BaseException:
                pass

    def delete_servers(self):
        servers = self.servers_client.list_servers()['servers']
        servers = [server['id'] for server in servers]
        for server in servers:
            try:
                self.delete_vm(server)
            except BaseException:
                pass

    def delete_volumes(self):
        volumes = self.volumes_client.list_volumes()['volumes']
        volumes = [volume['id'] for volume in volumes]
        for volume in volumes:
            try:
                self.delete_volume(volume)
            except BaseException:
                pass

    def delete_keypairs(self):
        kps = self.keypairs_client.list_keypairs()['keypairs']
        kps = [kp['keypair']['name'] for kp in kps]
        for kp in kps:
            try:
                self.delete_key_pair(kp)
            except BaseException:
                pass

    def delete_policies(self):
        policies = self.get_policy_list()
        for policy in policies:
            try:
                self.workload_policy_delete(policy)
            except BaseException:
                pass

    def delete_abandoned_ports(self):
        subnets = self.networks_client.show_network(
            CONF.network.internal_network_id)['network']['subnets']
        ports = self.network_client.list_ports()['ports']
        ports = [{'id': x['id'], 'device_id':x['device_id']}
                 for x in ports if x['fixed_ips'][0]['subnet_id'] in subnets]
        for port in ports:
            if port['device_id'] == '':
                try:
                    self.network_client.delete_port(port['id'])
                except BaseException:
                    pass

    def delete_securitygroups(self):
        sgs = self.security_groups_client.list_security_groups()[
            'security_groups']
        sgs = [sg['id'] for sg in sgs if sg['name'] != 'default']
        for sg in sgs:
            try:
                self.delete_security_group(sg)
            except BaseException:
                pass

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_cleaner(self):
        try:
            self.delete_restores()
            LOG.debug("\nrestores deleted\n")
            self.delete_snapshots()
            LOG.debug("\nsnapshots deleted\n")
            self.delete_workloads()
            LOG.debug("\nworkloads deleted\n")
            self.delete_servers()
            LOG.debug("\nvms deleted\n")
            self.delete_volumes()
            LOG.debug("\nvolumes deleted\n")
            self.delete_keypairs()
            LOG.debug("\nkeypairs deleted\n")
            self.delete_policies()
            LOG.debug("\npolicies deleted\n")
            self.delete_abandoned_ports()
            LOG.debug("\nAbandoned ports deleted\n")
            self.delete_securitygroups()
            LOG.debug("\nsecurity groups deleted\n")

        except Exception as e:
            LOG.error("Exception: " + str(e))
