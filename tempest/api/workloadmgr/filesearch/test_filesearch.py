import sys
import os
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

LOG = logging.getLogger(__name__)
CONF = config.CONF

class FilesearchTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(FilesearchTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
	reporting.add_test_script(str(__name__))

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_tvault_filesearchtest_api(self):
	try:
	    # Prerequisites
	    self.created = False
            self.workload_instances = []
	    filecount_in_snapshots = {}
	    volumes = ["/dev/vdb"]
            mount_points = ["mount_data_b"]

            # Launch instances
            self.create_key_pair(tvaultconf.key_pair_name)
            self.vm1_id = self.create_vm(vm_cleanup=False, key_pair=tvaultconf.key_pair_name)
            LOG.debug("VM-1 ID: " + str(self.vm1_id))
            self.vm2_id = self.create_vm(vm_cleanup=False, key_pair=tvaultconf.key_pair_name)
            LOG.debug("VM-2 ID: " + str(self.vm2_id))

            # Create volumes
            self.volume1_id = self.create_volume(tvaultconf.volume_size,tvaultconf.volume_type, volume_cleanup=False)
            LOG.debug("Volume ID: " + str(self.volume1_id))
            self.volume2_id = self.create_volume(tvaultconf.volume_size,tvaultconf.volume_type, volume_cleanup=False)
            LOG.debug("Volume ID: " + str(self.volume2_id))

            # Attach volume to the instance
            self.attach_volume(self.volume1_id, self.vm1_id, attach_cleanup=False)
            LOG.debug("Volume attached")
            self.attach_volume(self.volume2_id, self.vm2_id, attach_cleanup=False)
            LOG.debug("Volume attached")

            # Assign Floating IP's
            floating_ips_list = self.get_floating_ips()
            self.set_floating_ip(floating_ips_list[0], self.vm1_id)
            self.set_floating_ip(floating_ips_list[1], self.vm2_id)

            # Partitioning and  formatting the disk
            ssh1 = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ips_list[0]))
            self.execute_command_disk_create(ssh1, floating_ips_list[0], volumes, mount_points)
            ssh2 = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ips_list[1]))
            self.execute_command_disk_create(ssh2, floating_ips_list[1], volumes, mount_points)

            # Disk mounting
            self.execute_command_disk_mount(ssh1, floating_ips_list[0], volumes, mount_points)
            self.execute_command_disk_mount(ssh2, floating_ips_list[1], volumes, mount_points)
	    
            # Create workload
            self.workload_instances.append(self.vm1_id)
            self.workload_instances.append(self.vm2_id)
            self.wid = self.workload_create(self.workload_instances, tvaultconf.parallel, workload_name=tvaultconf.workload_name, workload_cleanup=False)
            LOG.debug("Workload ID: " + str(self.wid))
            time.sleep(5)
                
            # Create full snapshot 
            self.snapshot_id1 = self.workload_snapshot(self.wid, True, snapshot_cleanup=False)
            LOG.debug("Snapshot ID-1: " + str(self.snapshot_id1))
            #Wait till snapshot is complete
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id1)

	    # Add two files to vm1 to path /opt
            self.addCustomSizedfilesOnLinux(ssh1, "//opt", 2)

            # Create incremental snapshot
            self.snapshot_id2 = self.workload_snapshot(self.wid, False, snapshot_cleanup=False)
            LOG.debug("Snapshot ID-2: " + str(self.snapshot_id2))    
	    # Wait till snapshot is complete
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id2)

	    # Add two files to vm2 to path /home/ubuntu/mount_data_b
            self.addCustomSizedfilesOnLinux(ssh2, "//home/ubuntu/mount_data_b", 2)

            # Create incremental snapshot
            self.snapshot_id3 = self.workload_snapshot(self.wid, False, snapshot_cleanup=False)
            LOG.debug("Snapshot ID-3: " + str(self.snapshot_id3))
            # Wait till snapshot is complete
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id3)


	    # Add one  file to vm1 to path /home/ubuntu/mount_data_b
            self.addCustomSizedfilesOnLinux(ssh1, "//home/ubuntu/mount_data_b", 1)

	    # Create incremental snapshot
            self.snapshot_id4 = self.workload_snapshot(self.wid, False, snapshot_cleanup=False)
            LOG.debug("Snapshot ID-4: " + str(self.snapshot_id4))
            # Wait till snapshot is complete
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id4)

	    # Run Filesearch on vm-1
	    vmid_to_search = self.vm1_id
	    filepath_to_search = "/File_1.txt"
	    filecount_in_snapshots = {self.snapshot_id4 : 1}
	    filesearch_id = self.filepath_search(vmid_to_search, filepath_to_search)
	    snapshot_wise_filecount = self.verifyFilepath_Search(filesearch_id, filepath_to_search)
	    for snapshot_id in filecount_in_snapshots.keys():
    	        if snapshot_wise_filecount[snapshot_id] == filecount_in_snapshots[snapshot_id]:
		    filesearch_status = True
	        else:
		    filesearch_status = False
		    LOG.debug("Filepath Search unsuccessful")
                    reporting.add_test_step("Verification of Filepath serach", tvaultconf.FAIL)
	   	    raise Exception ("Filesearch path does not executed correctly")

	    if filesearch_status == True:
	        LOG.debug("Filepath_Search successful")
	    	reporting.add_test_step("Verification of Filepath serach", tvaultconf.PASS)
		reporting.set_test_script_status(tvaultconf.PASS)
                reporting.test_case_to_write()
		

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

