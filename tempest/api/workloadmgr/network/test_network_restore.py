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
            ntwrks = self.create_network()
            vms = {}
            nws = [x['id'] for x in ntwrks]
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
            if nt_bf == nt_af:
                reporting.add_test_step("Verify network details after network restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify network details after network restore", tvaultconf.FAIL)

            if sbnt_bf == sbnt_af:
                reporting.add_test_step("Verify subnet details after network restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify subnet details after network restore", tvaultconf.FAIL)

            if rt_bf == rt_af:
                reporting.add_test_step("Verify router details after network restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify router details after network restore", tvaultconf.FAIL)

            if intf_bf == intf_af:
                reporting.add_test_step("Verify interface details after network restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verify interface details after network restore", tvaultconf.FAIL)

            self.delete_vm(self.get_restored_vm_list(restore_id)[0])
            self.delete_network_topology()
    	    reporting.test_case_to_write()
            
 
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write
