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

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
        reporting.add_test_script(str(__name__))

    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_1_volume_booted(self):
        try:
            ### Create vm ###

            reporting.add_test_script(str(__name__))


            volume_id = self.create_volume(size=tvaultconf.bootfromvol_vol_size, image_id=CONF.compute.image_ref, volume_cleanup=False)
            self.set_volume_as_bootable(volume_id)
            self.block_mapping_details = [{ "source_type": "volume",
                            "delete_on_termination": "false",
                            "boot_index": 0,
                            "uuid": volume_id,
                            "destination_type": "volume"}]
            vm_id = self.create_vm(image_id="", block_mapping_data=self.block_mapping_details, vm_cleanup=False)

            ### Create workload ###

            workload_id=self.workload_create([vm_id],tvaultconf.parallel, workload_cleanup=True)
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

            ### Full snapshot ###

            snapshot_id=self.workload_snapshot(workload_id, True, snapshot_cleanup=True)
            LOG.debug("\nworkload id : {}\n".format(str(workload_id)))
            LOG.debug("\nsnapshot id : {}\n".format(str(snapshot_id)))    
            time.sleep(5)
            self.wait_for_workload_tobe_available(workload_id)
            if(self.getSnapshotStatus(workload_id, snapshot_id) == "available"):
                reporting.add_test_step("Create full snapshot of boot from volume instance", tvaultconf.PASS)
                LOG.debug("Full snapshot available!!")
            else:
                reporting.add_test_step("Create full snapshot of boot from volume instance", tvaultconf.FAIL)
                raise Exception("Snapshot creation failed")

            volume_snapshots = self.get_available_volume_snapshots()

            LOG.debug("\nvolume is : {}\n".format(str(volume_id)))
            LOG.debug("\nvolume snapshots : {}\n".format(str(volume_snapshots)))

            ### Incremental snapshot ###

            self.created = False
            LOG.debug("workload is:" + str(workload_id))

            create_snapshot = command_argument_string.incr_snapshot_create + workload_id
            LOG.debug("Create snapshot command: " + str(create_snapshot))
            rc = cli_parser.cli_returncode(create_snapshot)
            if rc != 0:
                reporting.add_test_step("Execute workload-snapshot command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step("Execute workload-snapshot command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            incr_snapshot_id = query_data.get_inprogress_snapshot_id(workload_id)
            LOG.debug("Incremental Snapshot ID: " + str(incr_snapshot_id))
            #Wait for incremental snapshot to complete
            wc = self.wait_for_snapshot_tobe_available(workload_id, incr_snapshot_id)
            if (str(wc) == "available"):
                reporting.add_test_step("Incremental snapshot", tvaultconf.PASS)
                LOG.debug("Workload incremental snapshot successfully completed")
                self.created = True
            if (self.created == False):
                reporting.add_test_step("Incremental snapshot", tvaultconf.FAIL)
                raise Exception ("Workload incremental snapshot did not get created")

            if (tvaultconf.cleanup == True):
                self.addCleanup(self.snapshot_delete,workload_id, incr_snapshot_id)

            ### Selective restore ###

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
            restore_id_1=self.snapshot_selective_restore(workload_id, snapshot_id, restore_cleanup=True, restore_name=tvaultconf.restore_name,
                                                            instance_details=instance_details, network_details=network_details)
            LOG.debug("\nRestore ID(selective) : {}\n".format(restore_id_1))
            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            if(self.getRestoreStatus(workload_id, snapshot_id, restore_id_1) == "available"):
                reporting.add_test_step("Selective restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("Selective restore", tvaultconf.FAIL)
                raise Exception("Selective restore failed")

            #Fetch instance details after restore
            vm_list  =  self.get_restored_vm_list(restore_id_1)
            LOG.debug("Restored vm(selective) ID : " + str(vm_list))

            for id in range(len(vm_list)):
                restored_vm_details_list.append(self.get_vm_details(vm_list[id]))
            LOG.debug("Restored vm details list: " + str(restored_vm_details_list))

            vms_details_after_restore = self.get_vms_details_list(restored_vm_details_list)
            LOG.debug("VM details after restore: " + str(vms_details_after_restore))

            #Compare the data before and after restore
            for i in range(len(vms_details_after_restore)):
                if(vms_details_after_restore[i]['network_name'] == int_net_1_name):
                    reporting.add_test_step("Network verification for instance-" + str(i+1), tvaultconf.PASS)
                else:
                    LOG.error("Expected network: " + str(int_net_1_name))
                    LOG.error("Restored network: " + str(vms_details_after_restore[i]['network_name']))
                    reporting.add_test_step("Network verification for instance-" + str(i+1), tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)

            restored_volumes = self.get_restored_volume_list(restore_id_1)
            LOG.debug("Restored volumes list: "+str(restored_volumes))


            ### Inplace restore ###

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
                reporting.add_test_step("Triggering In-Place restore via CLI", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step("Triggering In-Place restore via CLI", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            #get restore id from database
            restore_id_2 = query_data.get_snapshot_restore_id(incr_snapshot_id)
            LOG.debug("\nRestore ID(inplace) : {}\n".format(restore_id_2))
            self.wait_for_snapshot_tobe_available(workload_id, incr_snapshot_id)

            #get in-place restore status
            if(self.getRestoreStatus(workload_id, incr_snapshot_id, restore_id_2) == "available"):
                reporting.add_test_step("In-place restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("In-place restore", tvaultconf.FAIL)
                raise Exception("In-place restore failed")

            #Fetch instance details after restore
            vm_list  =  self.get_restored_vm_list(restore_id_2)
            LOG.debug("Restored vm(In-place) ID : " + str(vm_list))

            #Delete restore for snapshot
            if (tvaultconf.cleanup == True):
                self.addCleanup(self.restore_delete, workload_id, incr_snapshot_id, restore_id_2)

            ### Oneclick restore ###

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
                reporting.add_test_step("Execute snapshot-oneclick-restore command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step("Execute snapshot-oneclick-restore command", tvaultconf.PASS)
                LOG.debug("Command executed correctly")


            restore_id_3 = query_data.get_snapshot_restore_id(snapshot_id)
            LOG.debug("\nRestore ID(oneclick): {}\n".format(str(restore_id_3)))

            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            if(self.getRestoreStatus(workload_id, snapshot_id, restore_id_3) == "available"):
                reporting.add_test_step("One-click restore", tvaultconf.PASS)
                LOG.debug("One-click restore passed")
            else:
                reporting.add_test_step("One-click restore", tvaultconf.FAIL)
                LOG.debug("One-click restore failed")
                raise Exception("One-click restore failed")
            LOG.debug("One-click restore complete")

            restored_volumes = self.get_restored_volume_list(restore_id_3)
            vm_list  =  self.get_restored_vm_list(restore_id_3)

            LOG.debug("Restored vms : " + str(vm_list))
            if (tvaultconf.cleanup == True):
                self.addCleanup(self.restore_delete, workload_id, snapshot_id, restore_id_3)
                time.sleep(20)
                self.addCleanup(self.delete_restored_vms, vm_list, restored_volumes)
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
