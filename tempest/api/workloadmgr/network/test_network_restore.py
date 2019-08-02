import sys
import os
import json
sys.path.append(os.getcwd())
from tempest.api.workloadmgr import base
from tempest import config
from tempest import test
from oslo_log import log as logging
from tempest import tvaultconf
from tempest import reporting
import time
from tempest import command_argument_string
from tempest.util import cli_parser
from tempest.util import query_data
import subprocess

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
        reporting.add_test_script(str(__name__))

    def delete_existing_networks(self):
        LOG.debug("Deleting the existing networks")
        networkslist = self.networks_client.list_networks()['networks']

        for network in networkslist:
            if network['router:external'] == False:
                self.delete_network(network['id'])
            else:
                pass

    def create_network(self):
        routers = {}
        subnets = {}
        nets = {}
        for x in range(1,5):
            net = self.networks_client.create_network(**{'name':"Private-{}".format(x)})
            nets[net['network']['name']] = net['network']['id']
            subnetconfig = {'ip_version': 4, 'network_id':net['network']['id'], 'name': "PS-{}".format(x), 'gateway_ip': '10.10.{}.1'.format(x), 'cidr': '10.10.{}.0/24'.format(x)}
            subnet = self.subnets_client.create_subnet(**subnetconfig)
            subnets[subnet['subnet']['name']] = subnet['subnet']['id']

        for x in range(1,4):
            router = self.network_client.create_router(**{'name':"Router-{}".format(x)})
            routers[router['router']['name']] = router['router']['id']

        networkslist = self.networks_client.list_networks()['networks']
        publicnetwork = [ x['id'] for x in networkslist if x['router:external'] == True]
        subprocess.call(["neutron", "router-gateway-set", routers['Router-1'], publicnetwork[0]])
        subprocess.call(["neutron", "router-gateway-set", routers['Router-2'], publicnetwork[0]])
        self.network_client.add_router_interface_with_subnet_id(routers['Router-1'], subnets['PS-1'])
        self.network_client.add_router_interface_with_subnet_id(routers['Router-1'], subnets['PS-2'])
        self.network_client.add_router_interface_with_subnet_id(routers['Router-3'], subnets['PS-3'])
        self.network_client.add_router_interface_with_subnet_id(routers['Router-2'], subnets['PS-4'])
        portid = self.network_client.create_port(**{'network_id':nets['Private-2'], 'fixed_ips': [{'ip_address':'10.10.2.4'}]})['port']['id']
        self.network_client.add_router_interface_with_port_id(routers['Router-2'], portid)


    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_nr(self):
        try:
            reporting.add_test_script(str(__name__))            
            self.delete_existing_networks()
            self.create_network()

            networkslist = self.networks_client.list_networks()['networks']
            nws = [x['id'] for x in networkslist]
            networks = [{i:j for i,j in x.items() if i not in ('network_id', 'created_at', 'updated_at', 'id')} for x in networkslist]

            sbnt = self.subnets_client.list_subnets()['subnets']
            subnets = [{i:j for i,j in x.items() if i not in ('network_id', 'created_at', 'updated_at', 'id')} for x in sbnt]
  
            rs = self.network_client.list_routers()['routers']
            routers = [{i:j for i,j in x.items() if i not in ('external_gateway_info', 'created_at', 'updated_at', 'id')} for x in rs]

            interfaces = {}
            for router in self.get_router_ids():
                interfaceslist = self.network_client.list_router_interfaces(router)['ports']
                intrfs = [{i:j for i,j in x.items() if i not in ('network_id', 'created_at', 'updated_at', 'mac_address', 'fixed_ips', 'id', 'device_id')} for x in interfaceslist]
                interfaces[self.network_client.show_router(router)['router']['name']] = intrfs 
            vms = {}
            vmlist = []
            for net in nws:
                vmid = self.create_vm(networkid=[{'uuid':net}], vm_cleanup=True)
                vmlist.append(vmid)
                nw = self.networks_client.show_network(net)['network']
                ntwrk = {i:j for i,j in nw.items() if i not in ('subnets', 'created_at', 'updated_at', 'id')} 
                vms[vmid] = ntwrk

            workload_id=self.workload_create(vmlist,tvaultconf.parallel, workload_cleanup=True)
            LOG.debug("Workload ID: " + str(workload_id))
            if(workload_id != None):
                self.wait_for_workload_tobe_available(workload_id)
                if(self.getWorkloadStatus(workload_id) == "available"):
                    reporting.add_test_step("Create workload", tvaultconf.PASS)
                else:
                    reporting.add_test_step("Create workload", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Create workload", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("Workload creation failed")

            snapshot_id=self.workload_snapshot(workload_id, True, snapshot_cleanup=True)
            time.sleep(5)
            self.wait_for_workload_tobe_available(workload_id)
            if(self.getSnapshotStatus(workload_id, snapshot_id) == "available"):
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                LOG.debug("Full snapshot available!!")
            else:
                reporting.add_test_step("Create full snapshot", tvaultconf.FAIL)
                raise Exception("Snapshot creation failed")

            self.delete_vms(vmlist)
            self.delete_existing_networks()
	    reporting.test_case_to_write()
 
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write
