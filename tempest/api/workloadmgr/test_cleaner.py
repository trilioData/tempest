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

    def _delete_restores(self, snapshot_id, workload_id):
        rests = self.getRestoreList(snapshot_id)
        for res in rests:
            try:
                self.restore_delete(workload_id, snapshot_id, res)
            except BaseException:
                pass

    def _delete_snapshots(self, workload_id):
        snaps = self.getSnapshotList(workload_id)
        for snap in snaps:
            try:
                snapshot_status = self.getSnapshotStatus(workload_id, snap)
                if snapshot_status == 'mounted':
                    self.unmount_snapshot(workload_id, snap)
                self._delete_restores(snap, workload_id)
                self.wait_for_workload_tobe_available(workload_id,timeout=900)
                self.snapshot_delete(workload_id, snap)
            except BaseException:
                pass

    def _delete_workloads(self):
        wls = self.getWorkloadList()
        for wl in wls:
            try:
                self._delete_snapshots(wl)
                self.wait_for_workload_tobe_available(wl)
                self.workload_delete(wl)
            except BaseException:
                pass

    def _delete_servers(self):
        servers = self.servers_client.list_servers()['servers']
        servers = [server['id'] for server in servers]
        for server in servers:
            try:
                self.delete_vm(server)
            except BaseException:
                pass
        servers = self.servers_client.list_servers()['servers']
        LOG.debug(f"vms list at end of delete_servers: {servers}")

    def _delete_volumes(self):
        volumes = self.volumes_client.list_volumes()['volumes']
        volumes = [volume['id'] for volume in volumes]
        for volume in volumes:
            try:
                self.delete_volume(volume)
            except BaseException:
                pass

    def _delete_keypairs(self):
        kps = self.keypairs_client.list_keypairs()['keypairs']
        kps = [kp['keypair']['name'] for kp in kps]
        for kp in kps:
            try:
                self.delete_key_pair(kp)
            except BaseException:
                pass

    def _delete_policies(self):
        policies = self.get_policy_list()
        for policy in policies:
            try:
                self.workload_policy_delete(policy)
            except BaseException:
                pass

    def _delete_abandoned_ports(self):
        subnets = self.networks_client.show_network(
            CONF.network.internal_network_id)['network']['subnets']
        ports = self.ports_client.list_ports()['ports']
        ports = [{'id': x['id'], 'device_id':x['device_id']}
                 for x in ports if len(x['fixed_ips']) and \
                         x['fixed_ips'][0]['subnet_id'] in subnets]
        for port in ports:
            if port['device_id'] == '':
                try:
                    self.ports_client.delete_port(port['id'])
                except BaseException:
                    pass

    def _delete_securitygroups(self):
        sgs = self.list_security_groups()
        sgs = [sg['id'] for sg in sgs if sg['name'] != 'default']
        for sg in sgs:
            try:
                self.delete_security_group(sg)
            except BaseException:
                pass

    def _delete_quotas(self):
        quotas = self.get_quota_list(CONF.identity.tenant_id)
        LOG.debug(quotas)
        qs = [qt['id'] for qt in quotas]
        for qt in qs:
            try:
                self.delete_project_quota(qt)
            except Exception:
                pass

    def _delete_secrets(self):
        secrets = self.secret_client.list_secrets()['secrets']
        for secret in secrets:
            secret_uuid = secret['secret_ref'].split('/')[-1]
            try:
                self.delete_secret(secret_uuid)
            except BaseException:
                pass

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_cleaner(self):
        try:
            self._delete_workloads()
            LOG.debug("\nworkloads deleted\n")
            self._delete_servers()
            LOG.debug("\nvms deleted\n")
            self._delete_volumes()
            LOG.debug("\nvolumes deleted\n")
            self._delete_keypairs()
            LOG.debug("\nkeypairs deleted\n")
            self._delete_policies()
            LOG.debug("\npolicies deleted\n")
            self._delete_abandoned_ports()
            LOG.debug("\nAbandoned ports deleted\n")
            self._delete_securitygroups()
            LOG.debug("\nsecurity groups deleted\n")
            self._delete_quotas()
            LOG.debug("\nWorkloadmgr quotas deleted\n")
            self._delete_secrets()
            LOG.debug("\nSecrets deleted\n")

        except Exception as e:
            LOG.error("Exception: " + str(e))
