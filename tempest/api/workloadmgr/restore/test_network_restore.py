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
import random

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
        reporting.add_test_script(str(__name__))

    def delete_network_topology(self):
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
        for x in range(1,7):
            if x != 7:
                net = self.networks_client.create_network(**{'name':"Private-{}".format(x)})
                nets[net['network']['name']] = net['network']['id']
                subnetconfig = {'ip_version': 4, 'network_id':net['network']['id'], 'name': "PS-{}".format(x), 'gateway_ip': '10.10.{}.1'.format(x), 'cidr': '10.10.{}.0/24'.format(x)}
                subnet = self.subnets_client.create_subnet(**subnetconfig)
                subnets[subnet['subnet']['name']] = subnet['subnet']['id']
            else:
                net = self.networks_client.create_network(**{'name':"Private-{}".format(x), 'admin_state_up':'False', 'shared':'True'})
                nets[net['network']['name']] = net['network']['id']

        for x in range(1,6):
            if x != 4:
                router = self.network_client.create_router(**{'name':"Router-{}".format(x)})
            else:
                router = self.network_client.create_router(**{'name':"Router-{}".format(x), 'admin_state_up':'False'})
            routers[router['router']['name']] = router['router']['id']

        networkslist = self.networks_client.list_networks()['networks']
        self.network_client.add_router_interface_with_subnet_id(routers['Router-1'], subnets['PS-1'])
        self.network_client.add_router_interface_with_subnet_id(routers['Router-1'], subnets['PS-2'])
        self.network_client.add_router_interface_with_subnet_id(routers['Router-3'], subnets['PS-3'])
        self.network_client.add_router_interface_with_subnet_id(routers['Router-2'], subnets['PS-4'])
        portid1 = self.network_client.create_port(**{'network_id':nets['Private-2'], 'fixed_ips': [{'ip_address':'10.10.2.4'}]})['port']['id']
        self.network_client.add_router_interface_with_port_id(routers['Router-2'], portid1)
        portid2 = self.network_client.create_port(**{'network_id':nets['Private-2'], 'fixed_ips': [{'ip_address':'10.10.2.5'}]})['port']['id']
        portid3 = self.network_client.create_port(**{'network_id':nets['Private-2'], 'fixed_ips': [{'ip_address':'10.10.2.6'}]})['port']['id']
        self.network_client.add_router_interface_with_port_id(routers['Router-4'], portid2)
        self.network_client.add_router_interface_with_port_id(routers['Router-5'], portid3)
        self.network_client.add_router_interface_with_subnet_id(routers['Router-4'], subnets['PS-5'])
        portid4 = self.network_client.create_port(**{'network_id':nets['Private-5'], 'fixed_ips': [{'ip_address':'10.10.5.3'}]})['port']['id']
        self.network_client.add_router_interface_with_port_id(routers['Router-5'], portid4)
        
    def get_topology_details(self):
            networkslist = self.networks_client.list_networks()['networks']
            nws = [x['id'] for x in networkslist]
            nt= [{str(i):str(j) for i,j in x.items() if i not in ('network_id', 'subnets', 'created_at', 'updated_at', 'id')} for x in networkslist]
            networks = {}
            for each in nt:
                networks[each['name']] = each

            sbnt = self.subnets_client.list_subnets()['subnets']
            sbnts = [{str(i):str(j) for i,j in x.items() if i not in ('network_id', 'created_at', 'updated_at', 'id')} for x in sbnt]
            subnets = {}
            for each in sbnts:
                subnets[each['name']] = each


            rs = self.network_client.list_routers()['routers']
            rts = [{str(i):str(j) for i,j in x.items() if i not in ('external_gateway_info', 'created_at', 'updated_at', 'id')} for x in rs]
            routers = {}
            for each in rts:
                routers[each['name']] = each

            interfaces = {}
            for router in self.get_router_ids():
                interfaceslist = self.network_client.list_router_interfaces(router)['ports']
                intrfs = [{str(i):str(j) for i,j in x.items() if i not in ('network_id', 'created_at', 'updated_at', 'mac_address', 'fixed_ips', 'id', 'device_id', 'security_groups', 'port_security_enabled', 'revision_number')} for x in interfaceslist]
                interfaces[self.network_client.show_router(router)['router']['name']] = intrfs 
            return(networks, subnets, routers, interfaces)

    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_network_restore(self):
        try:
            reporting.add_test_script(str(__name__))            
            self.delete_network_topology()
            self.create_network()
            vms = {}
            nws = [x['id'] for x in ntwrks]
            import random 
            vmid = self.create_vm(vm_name="instance", networkid=[{'uuid':random.choice(nws)}], vm_cleanup=True)

            nt_bf, sbnt_bf, rt_bf, intf_bf = self.get_topology_details()
            

            workload_id=self.workload_create([vmid],tvaultconf.parallel, workload_cleanup=True)
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

            instance_details = []
            vm_name = "restored_instance"
            temp_instance_data = { 'id': vmid,
                                    'include': True,
                                   'restore_boot_disk': True,
                                   'name': vm_name,
                                   'vdisks':[]
                                 }
            instance_details.append(temp_instance_data)
            LOG.debug("Instance details for restore: " + str(instance_details))


            self.delete_vm(vmid)
            self.delete_network_topology()

            restore_id=self.snapshot_selective_restore(workload_id, snapshot_id,restore_name=tvaultconf.restore_name,
                                                            instance_details=instance_details,
                                                            network_restore_flag=True)

            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            if(self.getRestoreStatus(workload_id, snapshot_id, restore_id) == "available"):
                reporting.add_test_step("Selective restore with network restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("Selective restore with network restore", tvaultconf.FAIL)
                raise Exception("Selective restore with network restore failed")

            nt_af, sbnt_af, rt_af, intf_af = self.get_topology_details()

            if nt_bf == nt_af and sbnt_bf == sbnt_af and rt_bf == rt_af and intf_bf == intf_af:
                reporting.add_test_step("Network restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("Network restore", tvaultconf.FAIL)

            self.delete_vm(self.get_restored_vm_list(restore_id)[0])
            self.delete_network_topology()
    	    reporting.test_case_to_write()
            
 
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write
