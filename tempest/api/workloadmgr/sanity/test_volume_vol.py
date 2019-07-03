import sys
import os
import json
import tempest
import unicodedata
import collections
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

LOG = logging.getLogger(__name__)
CONF = config.CONF

class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']
    volumes = None

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
        reporting.add_test_script(str(__name__))

    def assign_floating_ips(self, vmid, cleanup):
        fip = self.get_floating_ips()
        LOG.debug("\nAvailable floating ips are : {}\n".format(fip))
        self.set_floating_ip(str(fip[0]),vmid,floatingip_cleanup=cleanup)
        return(fip[0])

    def data_ops(self, flo_ip, mount_point, file_count):
        global volumes
        ssh = self.SshRemoteMachineConnectionWithRSAKey(str(flo_ip))
        self.execute_command_disk_create(ssh, str(flo_ip), [volumes[0]], [mount_point])
        self.execute_command_disk_mount(ssh, str(flo_ip), [volumes[0]], [mount_point])
        self.addCustomfilesOnLinuxVM(ssh, mount_point, file_count)
        ssh.close()

    def calcmd5sum(self, flip, mount_point):
        mdb = {}
        ssh = self.SshRemoteMachineConnectionWithRSAKey(str(flip))
        mdb[str(flip)] = self.calculatemmd5checksum(ssh, mount_point)
        ssh.close()
        return mdb

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_1_volume_volume(self):
        try:
            ### VM and Workload ###

            reporting.add_test_script(str(__name__))

            deleted = 0
            global volumes
            mount_points = ["mount_data_a", "mount_data_b"]
            md5sums_dir_before = {}

            #Create Keypair
            kp = self.create_key_pair(tvaultconf.key_pair_name, keypair_cleanup=True)
            LOG.debug("Key_pair : "+str(kp))

            #Create bootable volume
            boot_volume_id = self.create_volume(image_id=CONF.compute.image_ref, volume_cleanup=False)
            self.set_volume_as_bootable(boot_volume_id)
            LOG.debug("Bootable Volume ID : "+str(boot_volume_id))

            self.block_mapping_details = [{ "source_type": "volume",
                            "delete_on_termination": "false",
                            "boot_index": 0,
                            "uuid": boot_volume_id,
                            "destination_type": "volume"}]

            #Create instance
            vm_id = self.create_vm(key_pair=kp, image_id="", block_mapping_data=self.block_mapping_details, vm_cleanup=False)
            LOG.debug("VM ID : "+str(vm_id))
            time.sleep(30)
            
            #Create and attach volume
            volume_id = self.create_volume(volume_type_id=CONF.volume.volume_type_id, volume_cleanup=False)
            LOG.debug("Volume ID: " + str(volume_id))
            volumes = tvaultconf.volumes_parts

            self.attach_volume(volume_id, vm_id, attach_cleanup=False)
            LOG.debug("Volume attached")

            #Assign floating IP
            floating_ip_1 = self.assign_floating_ips(vm_id, False)
            LOG.debug("Assigned floating IP : "+str(floating_ip_1))
            raise Exception("something")
            LOG.debug("Sleeping for 40 sec")
            time.sleep(40)

            #Adding data and calculating md5sums
            self.data_ops(floating_ip_1, mount_points[0], 3)
            LOG.debug("Created disk and mounted the attached volume")

            md5sums_dir_before = self.calcmd5sum(floating_ip_1, mount_points[0])
            LOG.debug("MD5sums for directory on original vm : "+str(md5sums_dir_before))


            workload_create = command_argument_string.workload_create + " --instance instance-id=" +str(vm_id)
            rc = cli_parser.cli_returncode(workload_create)
            if rc != 0:
                reporting.add_test_step("Execute workload-create command", tvaultconf.FAIL)
                raise Exception("Workload-create command did not execute correctly")
            else:
                reporting.add_test_step("Execute workload-create command", tvaultconf.PASS)
                LOG.debug("Workload-create command executed correctly")

            time.sleep(10)
            workload_id = query_data.get_workload_id(tvaultconf.workload_name)
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

            if (tvaultconf.cleanup == True):
                self.addCleanup(self.workload_delete, workload_id)

            ### Full Snapshot ###

            self.created = False

            #Create snapshot with CLI command
            create_snapshot = command_argument_string.snapshot_create + workload_id
            LOG.debug("Create snapshot command: " + str(create_snapshot))
            rc = cli_parser.cli_returncode(create_snapshot)
            if rc != 0:
                reporting.add_test_step("Execute workload-snapshot command with --full", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly for full snapshot")
            else:
                reporting.add_test_step("Execute workload-snapshot command with --full", tvaultconf.PASS)
                LOG.debug("Command executed correctly for full snapshot")

            snapshot_id = query_data.get_inprogress_snapshot_id(workload_id)
            LOG.debug("Snapshot ID: " + str(snapshot_id))
            wc = self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            if (str(wc) == "available"):
                reporting.add_test_step("Full snapshot", tvaultconf.PASS)
                self.created = True
            else:
                if (str(wc) == "error"):
                    pass
            if (self.created == False):
                reporting.add_test_step("Full snapshot", tvaultconf.FAIL)
                raise Exception ("Workload snapshot did not get created")

            if (tvaultconf.cleanup == True):
                self.addCleanup(self.snapshot_delete,workload_id, snapshot_id)

            LOG.debug("Sleeping for 40s")
            time.sleep(40)

            #Add some more data to files on VM
            ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip_1))
            self.addCustomfilesOnLinuxVM(ssh, mount_points[0], 2)
            ssh.close()

            ### Incremental snapshot ###

            self.created = False

            #Create incremental snapshot using CLI command
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
            restored_vm_details = []
            vms_details_after_restore = []
            temp_vdisks_data = []

            int_net_1_name = self.get_net_name(CONF.network.internal_network_id)
            LOG.debug("int_net_1_name" + str(int_net_1_name))
            int_net_1_subnets = self.get_subnet_id(CONF.network.internal_network_id)
            LOG.debug("int_net_1_subnet" + str(int_net_1_subnets))

            temp_vdisks_data.append([{  'id':volume_id,
                                        'availability_zone':CONF.volume.volume_availability_zone,
                                        'new_volume_type':CONF.volume.volume_type
                                    }])

            LOG.debug("Vdisks details for restore"+str(temp_vdisks_data))

            #Create instance details for restore.json
            vm_name = "tempest_test_vm_"+vm_id+"_selectively_restored"
            temp_instance_data = {  'id': vm_id,
                                    'availability_zone':CONF.compute.vm_availability_zone,
                                    'include': True,
                                    'restore_boot_disk': True,
                                    'name': vm_name,
                                    'vdisks':temp_vdisks_data[0]
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
            restore_id_1=self.snapshot_selective_restore(workload_id, snapshot_id,restore_name=tvaultconf.restore_name, restore_cleanup=True,
                                                            instance_details=instance_details, network_details=network_details)
            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            if(self.getRestoreStatus(workload_id, snapshot_id, restore_id_1) == "available"):
                reporting.add_test_step("Selective restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("Selective restore", tvaultconf.FAIL)
                raise Exception("Selective restore failed")

            #Fetch instance details after restore
            vm_list  =  self.get_restored_vm_list(restore_id_1)
            LOG.debug("Restored vm(selective) ID : " + str(vm_list))
            time.sleep(60)
            floating_ip_2 = self.assign_floating_ips(vm_list[0], True)
            LOG.debug("Floating ip assigned to selective restore vm -> "+str(floating_ip_2))
            md5sums_dir_after = {}
            ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip_2))
            self.execute_command_disk_mount(ssh, str(floating_ip_2), [volumes[0]], [mount_points[0]])
            time.sleep(5)
            md5sums_dir_after = self.calcmd5sum(floating_ip_2, mount_points[0])
            ssh.close()

            LOG.debug("MD5SUMS before restore")
            LOG.debug(md5sums_dir_before[str(floating_ip_1)])
            LOG.debug("MD5SUMS after restore")
            LOG.debug(md5sums_dir_after[str(floating_ip_2)])

            if md5sums_dir_before[str(floating_ip_1)] == md5sums_dir_after[str(floating_ip_2)]:
                LOG.debug("***MDSUMS MATCH***")
                reporting.add_test_step("Md5 Verification for volume", tvaultconf.PASS)
            else:
                LOG.debug("***MDSUMS DON'T MATCH***")
                reporting.add_test_step("Md5 Verification for volume", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            for id in range(len(vm_list)):
                restored_vm_details.append(self.get_vm_details(vm_list[id]))
            LOG.debug("Restored vm details list: " + str(restored_vm_details))

            vms_details_after_restore = self.get_vms_details_list(restored_vm_details)
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

            ### In-place restore ###

            #Create in-place restore with CLI command
            restore_command  = command_argument_string.inplace_restore + str(tvaultconf.restore_filename) + " "  + str(incr_snapshot_id)

            LOG.debug("inplace restore cli command: " + str(restore_command))
            #Restore.json with only volume 2 excluded
            restore_json = json.dumps({
            'openstack': {
                'instances': [{
                    'restore_boot_disk': True,
                    'include': True,
                    'id': vm_id,
                    'vdisks': [{
                            'restore_cinder_volume': True,
                            'id': volume_id,
                            'new_volume_type':CONF.volume.volume_type
                            }],
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
            self.wait_for_snapshot_tobe_available(workload_id, incr_snapshot_id)

            #get in-place restore status
            if(self.getRestoreStatus(workload_id, incr_snapshot_id, restore_id_2) == "available"):
                reporting.add_test_step("In-place restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("In-place restore", tvaultconf.FAIL)
                raise Exception("In-place restore failed")

            #Fetch instance details after restore
            vm_list = []
            vm_list  =  self.get_restored_vm_list(restore_id_2)
            LOG.debug("Restored vm(In-place) ID : " + str(vm_list))

            time.sleep(40)
            md5sums_dir_after = {}
            ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip_1))
            self.execute_command_disk_mount(ssh, str(floating_ip_1), [volumes[0]], [mount_points[0]])
            time.sleep(5)
            md5sums_dir_after = self.calcmd5sum(floating_ip_1, mount_points[0])
            ssh.close()

            LOG.debug("<----md5sums_dir_before---->")
            LOG.debug(md5sums_dir_before[str(floating_ip_1)])
            LOG.debug("<----md5sums_dir_after---->")
            LOG.debug(md5sums_dir_after[str(floating_ip_1)])

            if md5sums_dir_before[str(floating_ip_1)] == md5sums_dir_after[str(floating_ip_1)]:
                LOG.debug("***MDSUMS MATCH***")
                reporting.add_test_step("Md5 Verification for volume", tvaultconf.PASS)
            else:
                LOG.debug("***MDSUMS DON'T MATCH***")
                reporting.add_test_step("Md5 Verification for volume", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            #Delete restore for snapshot
            if (tvaultconf.cleanup == True):
                self.addCleanup(self.restore_delete, workload_id, incr_snapshot_id, restore_id_2)

            ### One-click restore ###

            mdb = self.calcmd5sum(floating_ip_1, mount_points[0])
            LOG.debug("MD5SUMS before deleting the instance for one click restore : "+str(mdb))

            self.disassociate_floating_ip_from_server(floating_ip_1, vm_id)
            self.detach_volume(vm_id, volume_id)

            #Delete the original instance
            self.delete_vm(vm_id)
            LOG.debug("Instance deleted successfully for one click restore : "+str(vm_id))
            time.sleep(10)

            #Delete bootable volume of original instance
            self.delete_volume(boot_volume_id)
            LOG.debug("Bootable volume of original instance deleted")            

            #Delete volume attached to original instance
            self.delete_volume(volume_id)
            LOG.debug("Volumes deleted successfully for one click restore : "+str(volume_id))

            deleted = 1

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
            LOG.debug("Restore ID: " + str(restore_id_3))

            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            if(self.getRestoreStatus(workload_id, snapshot_id, restore_id_3) == "available"):
                reporting.add_test_step("One-click restore", tvaultconf.PASS)
                LOG.debug("One-click restore passed")
            else:
                reporting.add_test_step("One-click restore", tvaultconf.FAIL)
                LOG.debug("One-click restore failed")
                raise Exception("One-click restore failed")
            LOG.debug("One-click restore complete")

            #Fetch instance details after restore
            vm_list = []
            vm_list  =  self.get_restored_vm_list(restore_id_3)
            LOG.debug("Restored vms : " + str(vm_list))

            mda = {}
            ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip_1))
            self.execute_command_disk_mount(ssh, str(floating_ip_1), [volumes[0]], [mount_points[0]])
            time.sleep(5)
            mda = self.calcmd5sum(floating_ip_1, mount_points[0])
            LOG.debug("MD5SUMS after deleting the instance for one click restore : "+str(mda))
            ssh.close()

            if mdb[str(floating_ip_1)] == mda[str(floating_ip_1)]:
                LOG.debug("***MDSUMS MATCH***")
                reporting.add_test_step("Md5 Verification for volume", tvaultconf.PASS)
            else:
                LOG.debug("***MDSUMS DON'T MATCH***")
                reporting.add_test_step("Md5 Verification for volume", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            restored_volumes = []
            restored_volumes = self.get_restored_volume_list(restore_id_3)
            LOG.debug("Restored volumes : ")
            LOG.debug(restored_volumes)

            if (tvaultconf.cleanup == True):
                self.addCleanup(self.restore_delete, workload_id, snapshot_id, restore_id_3)
                time.sleep(30)
                self.addCleanup(self.delete_restored_vms, vm_list, restored_volumes)

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            if (deleted == 0):
                self.disassociate_floating_ip_from_server(floating_ip_1, vm_id)
                self.detach_volume(vm_id, volume_id)
                self.delete_vm(vm_id)
                time.sleep(10)
                self.delete_volume(volume_id)
                self.delete_volume(boot_volume_id)
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
