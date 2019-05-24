#Copyright 2014 IBM Corp.
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

import os
from tempest.api.workloadmgr import base
from tempest import config
from tempest import test
import json
import sys
from tempest import api
from oslo_log import log as logging
from tempest.common import waiters
from tempest import tvaultconf
from tempest import reporting
from tempest.util import query_data
from tempest.util import cli_parser
sys.path.append(os.getcwd())
import time
from tempest import command_argument_string

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']
    workload_id = None
    snapshot_id = None
    incr_snapshot_id = None
    vm_id = None
    volume_id = None
    volume_snapshots = None
    counter = None

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
        reporting.add_test_script(str(__name__))

    @test.pre_req({'type':'bootfromvol_workload'})
    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_1_fullsnapshot(self):
        try:
            global counter
            global vm_id
            global workload_id
            global snapshot_id
            global volume_id
            global volume_snapshots
            counter=1
            x="a"
            reporting.setup_report("Tests")
            reporting.add_test_script(str(counter)+". "+str(__name__).split('.')[-1]+ "_create_full_snapshot")

            #Create full snapshot
            self.snapshot_id=self.workload_snapshot(self.workload_id, True, snapshot_cleanup=False)
            workload_id = self.workload_id
            snapshot_id = self.snapshot_id
            LOG.debug("workload id--------> : "+str(workload_id))
            LOG.debug("snapshot id--------> : "+str(snapshot_id))    
            time.sleep(5)
            self.wait_for_workload_tobe_available(self.workload_id)
            if(self.getSnapshotStatus(self.workload_id, self.snapshot_id) == "available"):
                reporting.add_test_step("{}. Create full snapshot of boot from volume instance".format(x), tvaultconf.PASS)
                LOG.debug("Full snapshot available!!")
            else:
                reporting.add_test_step("{}. Create full snapshot of boot from volume instance".format(x), tvaultconf.FAIL)
                raise Exception("Snapshot creation failed")
 
            volume_id = self.volume_id
            vm_id = self.vm_id

            self.volume_snapshots = self.get_available_volume_snapshots()
            volume_snapshots = self.volume_snapshots

            LOG.debug("workload is : " + str(workload_id))
            LOG.debug("vm id : " + str(vm_id))
            LOG.debug("volume is : " + str(volume_id))
            LOG.debug("snapshot id : " + str(snapshot_id))
            LOG.debug("volume snapshots : "+ str(volume_snapshots))
            reporting.test_case_to_write()
            counter+=1

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()


    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_2_create_incremental_snapshot(self):
        try:
            global counter
            global workload_id
            global incr_snapshot_id
            x="a"
            reporting.add_test_script(str(counter)+". "+str(__name__).split('.')[-1]+ "_create_incremental_snapshot")
            self.created = False
            LOG.debug("workload is:" + str(workload_id))

        #Create incremental snapshot using CLI command
            create_snapshot = command_argument_string.incr_snapshot_create + workload_id
            LOG.debug("Create snapshot command: " + str(create_snapshot))
            rc = cli_parser.cli_returncode(create_snapshot)
            if rc != 0:
                reporting.add_test_step("{}. Execute workload-snapshot command".format(x), tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step("{}. Execute workload-snapshot command".format(x), tvaultconf.PASS)
                LOG.debug("Command executed correctly")
            x=chr(ord(x)+1)

            self.incr_snapshot_id = query_data.get_inprogress_snapshot_id(workload_id)
            LOG.debug("Incremental Snapshot ID: " + str(self.incr_snapshot_id))
            incr_snapshot_id = self.incr_snapshot_id
            #Wait for incremental snapshot to complete
            wc = self.wait_for_snapshot_tobe_available(workload_id, self.incr_snapshot_id)
            if (str(wc) == "available"):
                reporting.add_test_step("{}. Incremental snapshot".format(x), tvaultconf.PASS)
                LOG.debug("Workload incremental snapshot successfully completed")
                self.created = True
            if (self.created == False):
                reporting.add_test_step("{}. Incremental snapshot".format(x), tvaultconf.FAIL)
                raise Exception ("Workload incremental snapshot did not get created")

            reporting.test_case_to_write()
            counter+=1


        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()


    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c2')
    def test_3_selective_restore(self):
        try:
            global snapshot_id
            global workload_id
            global counter
            x="a"
            reporting.add_test_script(str(counter)+". "+str(__name__).split('.')[-1]+ "_selective_restore")
            instance_details = []
            network_details  = []
            restored_vm_details_list = []
            vms_details_after_restore = []
            int_net_1_name = self.get_net_name(CONF.network.internal_network_id)
            LOG.debug("int_net_1_name" + str(int_net_1_name))
            int_net_1_subnets = self.get_subnet_id(CONF.network.internal_network_id)
            LOG.debug("int_net_1_subnet" + str(int_net_1_subnets))

            #Create instance details for restore.json


            vm_name = "tempest_test_vm_"+vm_id+"_restored"
            temp_instance_data = { 'id': vm_id,
                   'availability_zone':CONF.compute.vm_availability_zone,
                                   'include': True,
                                   'restore_boot_disk': True,
                                   'name': vm_name
                                    }
            instance_details.append(temp_instance_data)
            LOG.debug("Instance details for restore: " + str(instance_details))

            #Create network details for restore.json
            snapshot_network = {
                                 'id': CONF.network.internal_network_id,
                                 'subnet': { 'id': int_net_1_subnets }
                               }
            target_network = { 'name': int_net_1_name,
                               'id': CONF.network.internal_network_id,
                               'subnet': { 'id': int_net_1_subnets }
                             }
            network_details = [ { 'snapshot_network': snapshot_network,
                                       'target_network': target_network } ]
            LOG.debug("Network details for restore: " + str(network_details))


            LOG.debug("Snapshot id : " + str(snapshot_id))
            #Trigger selective restore
            restore_id=self.snapshot_selective_restore(workload_id, snapshot_id,restore_name=tvaultconf.restore_name,
                                                            instance_details=instance_details, network_details=network_details)
            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            if(self.getRestoreStatus(workload_id, snapshot_id, restore_id) == "available"):
                reporting.add_test_step("{}. Selective restore".format(x), tvaultconf.PASS)
            else:
                reporting.add_test_step("{}. Selective restore".format(x), tvaultconf.FAIL)
                raise Exception("Selective restore failed")
            x=chr(ord(x)+1)

            #Fetch instance details after restore
            vm_list  =  self.get_restored_vm_list(restore_id)
            LOG.debug("Restored vm(selective) ID : " + str(vm_list))

            for id in range(len(vm_list)):
                restored_vm_details_list.append(self.get_vm_details(vm_list[id]))
            LOG.debug("Restored vm details list: " + str(restored_vm_details_list))

            vms_details_after_restore = self.get_vms_details_list(restored_vm_details_list)
            LOG.debug("VM details after restore: " + str(vms_details_after_restore))

            #Compare the data before and after restore
            for i in range(len(vms_details_after_restore)):
                if(vms_details_after_restore[i]['network_name'] == int_net_1_name):
                    reporting.add_test_step("{}. Network verification for instance-".format(x) + str(i+1), tvaultconf.PASS)
                else:
                    LOG.error("Expected network: " + str(int_net_1_name))
                    LOG.error("Restored network: " + str(vms_details_after_restore[i]['network_name']))
                    reporting.add_test_step("{}. Network verification for instance-".format(x) + str(i+1), tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)

            restored_volumes = self.get_restored_volume_list(restore_id)
            LOG.debug("Restored volumes list: "+str(restored_volumes))

            #Delete VM
            self.delete_vm(vm_list[0])
            LOG.debug("Deleted selectively restored vm successfully")
            time.sleep(10)

            #Delete restored volume
            self.delete_volume(restored_volumes[0])
            LOG.debug("Deleted restored volume successfully")

            #Delete restore for snapshot
            self.restore_delete(workload_id, snapshot_id, restore_id)
            LOG.debug("Snapshot Restore(selective) deleted successfully")


            reporting.test_case_to_write()
            counter+=1

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_4_inplace_restore(self):
        try:
            global counter
            global incr_snapshot_id
            global vm_id
            x="a"
            reporting.add_test_script(str(counter)+". "+str(__name__).split('.')[-1]+ "_in-place_restore")
            #Create in-place restore with CLI command
            restore_command  = command_argument_string.inplace_restore + str(tvaultconf.restore_filename) + " "  + str(incr_snapshot_id)

            LOG.debug("inplace restore cli command: " + str(restore_command))
            #Restore.json with only volume 2 excluded
            restore_json = json.dumps({
            'openstack': {
                'instances': [{
                    'restore_boot_disk': True,
                    'include': True,
                    'id': vm_id
                }],
                'networks_mapping': {
                    'networks': []
                }
            },
            'restore_type': 'inplace',
            'type': 'openstack'
    })
            LOG.debug("restore.json for inplace restore: " + str(restore_json))
            #Create Restore.json
            with open(tvaultconf.restore_filename, 'w') as f:
                f.write(str(json.loads(restore_json)))
            rc = cli_parser.cli_returncode(restore_command)
            if rc != 0:
                reporting.add_test_step("{}. Triggering In-Place restore via CLI".format(x), tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step("{}. Triggering In-Place restore via CLI".format(x), tvaultconf.PASS)
                LOG.debug("Command executed correctly")
            x=chr(ord(x)+1)

            #get restore id from database
            restore_id = query_data.get_snapshot_restore_id(incr_snapshot_id)
            self.wait_for_snapshot_tobe_available(workload_id, incr_snapshot_id)

            #get in-place restore status
            if(self.getRestoreStatus(workload_id, incr_snapshot_id, restore_id) == "available"):
                reporting.add_test_step("{}. In-place restore".format(x), tvaultconf.PASS)
            else:
                reporting.add_test_step("{}. In-place restore".format(x), tvaultconf.FAIL)
                raise Exception("In-place restore failed")

            #Fetch instance details after restore
            vm_list  =  self.get_restored_vm_list(restore_id)
            LOG.debug("Restored vm(In-place) ID : " + str(vm_list))

            #Delete restore for snapshot
            self.restore_delete(workload_id, snapshot_id, restore_id)
            LOG.debug("Snapshot Restore(in-place) deleted successfully")

            #Delete snapshot
            self.snapshot_delete(workload_id, incr_snapshot_id)
            LOG.debug("Incremental snapshot deleted successfully")

            reporting.test_case_to_write()
            counter+=1

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()



    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_5_oneclick_restore(self):
        try:
            global workload_id
            global snapshot_id
            global vm_id
            global volume_id
            global volume_snapshots
            global counter
            x="a"
            reporting.add_test_script(str(counter)+". "+str(__name__).split('.')[-1]+ "_one-click_restore")
            #Delete the original instance
            self.delete_vm(vm_id)
            LOG.debug("Instance deleted successfully for one click restore : "+str(vm_id))
            time.sleep(10)
            self.delete_volume(volume_id)
            LOG.debug("Volume deleted successfully for one click restore : "+str(volume_id))


            #Create one-click restore using CLI command
            restore_command = command_argument_string.oneclick_restore + " " + snapshot_id
            rc = cli_parser.cli_returncode(restore_command)
            if rc != 0:
                reporting.add_test_step("{}. Execute snapshot-oneclick-restore command".format(x), tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step("{}. Execute snapshot-oneclick-restore command".format(x), tvaultconf.PASS)
                LOG.debug("Command executed correctly")
            x=chr(ord(x)+1)

            wc = query_data.get_snapshot_restore_status(tvaultconf.restore_name,snapshot_id)
            LOG.debug("Snapshot restore status: " + str(wc))
            while (str(wc) != "available" or str(wc)!= "error"):
                time.sleep (5)
                wc = query_data.get_snapshot_restore_status(tvaultconf.restore_name, snapshot_id)
                LOG.debug("Snapshot restore status: " + str(wc))
                if (str(wc) == "available"):
                    LOG.debug("Snapshot Restore successfully completed")
                    reporting.add_test_step("{}. Snapshot one-click restore verification with DB".format(x), tvaultconf.PASS)
                    self.created = True
                    break
                else:
                    if (str(wc) == "error"):
                        break

            if (self.created == False):
                reporting.add_test_step("{}. Snapshot one-click restore verification with DB".format(x), tvaultconf.FAIL)
                raise Exception ("Snapshot Restore did not get created")

            LOG.debug("Snapshot ID :"+str(snapshot_id))
            restore_id = query_data.get_snapshot_restore_id(snapshot_id)
            LOG.debug("Restore ID: " + str(restore_id))

            vm_ids = query_data.get_vmids()
            LOG.debug("VMs : "+str(vm_ids))

            #Fetch instance details after restore
            vm_list  =  self.get_restored_vm_list(restore_id)
            LOG.debug("Restored vms : " + str(vm_list))

            #Fetch restored volumes
            restored_volumes = self.get_restored_volume_list(restore_id)
            LOG.debug("Restored volumes list: "+str(restored_volumes))

            #Delete the restored instance
            self.delete_vm(vm_list[0])
            LOG.debug("Restored instance deleted successfully")
            
            #Delete restored volume
            self.delete_volume(restored_volumes[0])
            LOG.debug("Deleted restored volume successfully") 
 
            #Delete restore for snapshot
            self.restore_delete(workload_id, snapshot_id, restore_id)
            LOG.debug("Snapshot Restore(one-click) deleted successfully")

            #Delete snapshot
            self.snapshot_delete(workload_id, snapshot_id)
            LOG.debug("Full snapshot deleted successfully")

            #Delete workload
            self.workload_delete(workload_id)
            LOG.debug("Workload deleted successfully")

            reporting.test_case_to_write()
            counter+=1
            reporting.end_report_table()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
