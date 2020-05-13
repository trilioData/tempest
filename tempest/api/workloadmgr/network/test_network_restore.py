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

    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_network_restore(self):
        try:
            reporting.add_test_script(str(__name__))            
            self.delete_network_topology()
            vms = []
            ntwrks = self.create_network()
            for network in ntwrks:
                if network['name'] in ['Private-1','Private-2','Private-5']:
                    vm_name = "instance-{}".format(network['name'])
                    vmid = self.create_vm(vm_name=vm_name, networkid=[{'uuid':network['id']}], vm_cleanup=True)
                    vms.append((vm_name, vmid))
            LOG.debug("Launched vms : {}".format(vms))
            
            nws = [x['id'] for x in ntwrks]

            nt_bf, sbnt_bf, rt_bf, intf_bf = self.get_topology_details()
           
            vms_ids = [x[1] for x in vms] 
            workload_id=self.workload_create(vms_ids,tvaultconf.parallel, workload_cleanup=True)
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
            for vm in vms:
                temp_instance_data = { 'id': vm[1],
                                        'include': True,
                                       'restore_boot_disk': True,
                                       'name': vm[0]+"restored_instance",
                                       'vdisks':[]
                                     }
                instance_details.append(temp_instance_data)
            LOG.debug("Instance details for restore: " + str(instance_details))

            vm_details_bf = {}
            for vm in vms:
                vm_details_bf[vm[0]] = self.get_vm_details(vm[1])['server']
                self.delete_vm(vm[1])
            self.delete_network_topology()

            restore_id=self.snapshot_selective_restore(workload_id, snapshot_id,restore_name=tvaultconf.restore_name,
                                                            instance_details=instance_details,
                                                            network_restore_flag=True, restore_cleanup=True)

            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            if(self.getRestoreStatus(workload_id, snapshot_id, restore_id) == "available"):
                reporting.add_test_step("Selective restore with network restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("Selective restore with network restore", tvaultconf.FAIL)
                raise Exception("Selective restore with network restore failed")

            nt_af, sbnt_af, rt_af, intf_af = self.get_topology_details()
            if nt_bf == nt_af:
                reporting.add_test_step("Verify network details after network restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify network details after network restore", tvaultconf.FAIL)
                LOG.error("Network details before and after restore: {0}, {1}".format(nt_bf, nt_af))

            if sbnt_bf == sbnt_af:
                reporting.add_test_step("Verify subnet details after network restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify subnet details after network restore", tvaultconf.FAIL)
                LOG.error("Subnet details before and after restore: {0}, {1}".format(sbnt_bf, sbnt_af))

            if rt_bf == rt_af:
                reporting.add_test_step("Verify router details after network restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify router details after network restore", tvaultconf.FAIL)
                LOG.error("Router details before and after restore: {0}, {1}".format(rt_bf, rt_af))

            if intf_bf == intf_af:
                reporting.add_test_step("Verify interface details after network restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify interface details after network restore", tvaultconf.FAIL)
                LOG.error("Interface details before and after restore: {0}, {1}".format(intf_bf, intf_af))

            vm_details_af = {}
            restored_vms = self.get_restored_vm_list(restore_id)
            for vm in restored_vms:
                vm_details = self.get_vm_details(vm)['server']
                vm_details_af[vm_details['name'].replace('restored_instance', '')] = vm_details
           
            klist = vm_details_bf.keys()
            klist.sort()

            for vm in klist:
                netname = vm_details_bf[vm]['addresses'].keys()[0]
                vm_details_bf[vm]['addresses'][netname][0]['OS-EXT-IPS-MAC:mac_addr'] = ''
                vm_details_af[vm]['addresses'][netname][0]['OS-EXT-IPS-MAC:mac_addr'] = ''
                vm_details_bf[vm]['links'][1]['href'] = ''
                vm_details_af[vm]['links'][1]['href'] = ''
                del vm_details_af[vm]['metadata']['config_drive']
                del vm_details_af[vm]['metadata']['ordered_interfaces']
                del vm_details_bf[vm]['links']
                del vm_details_af[vm]['links']
                vm_details_bf[vm]['OS-EXT-SRV-ATTR:instance_name'] = ''
                vm_details_af[vm]['OS-EXT-SRV-ATTR:instance_name'] = ''
                vm_details_bf[vm]['updated'] = ''
                vm_details_af[vm]['updated'] = ''
                vm_details_bf[vm]['created'] = ''
                vm_details_af[vm]['created'] = ''
                vm_details_bf[vm]['id'] = ''
                vm_details_af[vm]['id'] = ''
                vm_details_bf[vm]['OS-SRV-USG:launched_at'] = ''
                vm_details_af[vm]['OS-SRV-USG:launched_at'] = ''
                vm_details_af[vm]['name'] = vm_details_af[vm]['name'].replace('restored_instance', '')                
                        
            if vm_details_bf == vm_details_af:
                reporting.add_test_step("Verify instance details after restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify instance details after restore", tvaultconf.FAIL)
                LOG.error("Instance details before and after restore: {0}, {1}".format(vm_details_bf, vm_details_af))

            for rvm in restored_vms:
                self.delete_vm(rvm) 
            self.delete_network_topology()
            
            reporting.test_case_to_write()
 
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write
