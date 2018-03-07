from oslo_log import log as logging
LOG = logging.getLogger(__name__)
from tempest import tvaultconf, reporting
import time
import datetime
from tempest import config
from tempest import command_argument_string
from tempest.util import cli_parser
import collections
from random import randint

CONF = config.CONF

def small_workload(self):
    LOG.debug("Running prerequisites for : small_workload")
    #Create volume
    self.volume_id = self.create_volume(volume_cleanup=False)
    LOG.debug("Volume ID: " + str(self.volume_id))
    
    #create vm
    self.vm_id = self.create_vm(vm_cleanup=False)
    LOG.debug("Vm ID: " + str(self.vm_id))

    #Attach volume to the instance
    self.attach_volume(self.volume_id, self.vm_id,attach_cleanup=False)
    LOG.debug("Volume attached")

def inplace(self):
    try:
	self.exception=""
        self.total_workloads=1
        self.vms_per_workload=2
        self.volume_size=1
        self.total_volumes=3
        self.volumes_list = []
        self.workload_instances = []
        self.workload_volumes = []
        self.workloads = []
        self.full_snapshots = []
        self.restores = []
        self.fingerprint = ""
        self.vm_details_list = []
        self.vms_details = []
        self.floating_ips_list = []
        self.original_fingerprint = ""
        self.vm_list = []
        self.restored_vm_details_list = []
        self.floating_ips_list_after_restore = []
        self.vms_details_after_restore = []
        self.instance_details = []
        self.network_details = []
        volumes = tvaultconf.volumes_parts 
        mount_points = ["mount_data_b", "mount_data_c"]
        self.original_fingerprint = self.create_key_pair(tvaultconf.key_pair_name)
        ts = str(datetime.datetime.now()).replace('.','-')
        security_group_id = self.create_security_group("sec_group_{}".format(tvaultconf.security_group_name+ts)," security group {}".format("test_sec"), secgrp_cleanup=True)
        self.add_security_group_rule(parent_group_id = security_group_id, ip_protocol="TCP", from_port = "1", to_port= randint(1, 65535)
)
        self.add_security_group_rule(parent_group_id = security_group_id, ip_protocol="UDP", from_port = "1", to_port= randint(1, 65535)
)
        self.add_security_group_rule(parent_group_id = security_group_id, ip_protocol="TCP", from_port = 22, to_port= 22)
        flavor_id = self.get_flavor_id(tvaultconf.flavor_name)
        if(flavor_id == 0):
            flavor_id = self.create_flavor(tvaultconf.flavor_name)
        self.original_flavor_conf = self.get_flavor_details(flavor_id)

        for volume in range(self.total_volumes):
            volume_id = self.create_volume()
            self.volumes_list.append(str(volume_id))
        LOG.debug(str(self.total_volumes) + " volumes created: " + str(self.volumes_list))

        vm_name = "tempest_test_vm_1"
        vm_id = self.create_vm(vm_name=vm_name ,security_group_id=security_group_id,flavor_id=flavor_id, key_pair=tvaultconf.key_pair_name, vm_cleanup=True)
        self.workload_instances.append(vm_id)
        self.workload_volumes.append(self.volumes_list[0])
        self.attach_volume(str(self.volumes_list[0]), vm_id, device=volumes[0])

        vm_name = "tempest_test_vm_2"
        vm_id = self.create_vm(vm_name=vm_name ,security_group_id=security_group_id,flavor_id=flavor_id, key_pair=tvaultconf.key_pair_name, vm_cleanup=True)
        self.workload_instances.append(vm_id)
        self.workload_volumes.append(self.volumes_list[1])
        self.workload_volumes.append(self.volumes_list[2])
        self.attach_volume(self.volumes_list[1], vm_id, device=volumes[0])
        self.attach_volume(self.volumes_list[2], vm_id, device=volumes[1])

        for id in range(len(self.workload_instances)):
            available_floating_ips = self.get_floating_ips()
            if(len(available_floating_ips) > 0):
                floating_ip = self.get_floating_ips()[0]
            else:
		self.exception = "Floating ips not available"
                raise Exception(self.exception)
            self.floating_ips_list.append(floating_ip)
            self.set_floating_ip(str(floating_ip), self.workload_instances[id])

        
        ssh = self.SshRemoteMachineConnectionWithRSAKey(str(self.floating_ips_list[0]))
        self.execute_command_disk_create(ssh, str(self.floating_ips_list[0]),[volumes[0]],[mount_points[0]])
        ssh.close()

        ssh = self.SshRemoteMachineConnectionWithRSAKey(str(self.floating_ips_list[0]))
        self.execute_command_disk_mount(ssh, str(self.floating_ips_list[0]),[volumes[0]],[mount_points[0]])
        ssh.close()

        ssh = self.SshRemoteMachineConnectionWithRSAKey(str(self.floating_ips_list[1]))
        self.execute_command_disk_create(ssh, str(self.floating_ips_list[1]),volumes,mount_points)
        ssh.close()
        
        ssh = self.SshRemoteMachineConnectionWithRSAKey(str(self.floating_ips_list[1]))
        self.execute_command_disk_mount(ssh, str(self.floating_ips_list[1]),volumes,mount_points)
        ssh.close()

        #Fetch instance details before restore
        for id in range(len(self.workload_instances)):
            self.vm_details_list.append(self.get_vm_details(self.workload_instances[id]))
            
        self.vms_details = self.get_vms_details_list(self.vm_details_list)
        LOG.debug("vm details list before backups" + str( self.vm_details_list))
        LOG.debug("vm details dir before backups" + str( self.vms_details))

        #Fill some data on each of the volumes attached     
        ssh = self.SshRemoteMachineConnectionWithRSAKey(str(self.floating_ips_list[0]))
        self.addCustomSizedfilesOnLinux(ssh, mount_points[0], 3)
        ssh.close()

        ssh = self.SshRemoteMachineConnectionWithRSAKey(str(self.floating_ips_list[1]))
        self.addCustomSizedfilesOnLinux(ssh, mount_points[0], 3)
        self.addCustomSizedfilesOnLinux(ssh, mount_points[1], 3)
        ssh.close()

        #Create workload and trigger full snapshot
        self.workload_id=self.workload_create(self.workload_instances,tvaultconf.parallel)
        self.snapshot_id=self.workload_snapshot(self.workload_id, True)
        self.wait_for_workload_tobe_available(self.workload_id)
        if(self.getSnapshotStatus(self.workload_id, self.snapshot_id) != "available"):
	    self.exception = "Full Snapshot Failed"
            raise Exception(self.exception) 

        #delete Some Files on volumes
        ssh = self.SshRemoteMachineConnectionWithRSAKey(str(self.floating_ips_list[0]))
        self.deleteSomefilesOnLinux(ssh, mount_points[0], 1)
        ssh.close()

        ssh = self.SshRemoteMachineConnectionWithRSAKey(str(self.floating_ips_list[1]))
        self.deleteSomefilesOnLinux(ssh, mount_points[0], 1)
        self.deleteSomefilesOnLinux(ssh, mount_points[1], 1)
        ssh.close()
 
        self.incr_snapshot_id=self.workload_snapshot(self.workload_id, False)
        self.wait_for_workload_tobe_available(self.workload_id)
        if(self.getSnapshotStatus(self.workload_id, self.incr_snapshot_id) != "available"):
	    self.exception = "Incremental Snapshot Failed"
            raise Exception(self.exception)
    except Exception as self.exception:
        LOG.error("Exception" + str(self.exception))

def load_prerequisites_data(self, type):
     self.workload_instances = []
     if type == 'small_workload':
	totalVms = 2
     for vm in range(0,totalVms):
        if(tvaultconf.vms_from_file):
            flag=0
            flag=self.is_vm_available()
            if(flag != 0):
		server_id=self.read_vm_id() 
		self.workload_instances.append(server_id)
	    else:
		LOG.debug("vms not available in vms_file")
		raise Exception ("vms not available in vms_file, pre_requisites loading failed.")

def bootfrom_image_with_floating_ips(self):
    try:
        self.exception = ""
        self.total_workloads=1
        self.vms_per_workload=2
        self.volume_size=1
        self.workload_instances = []
        self.workload_volumes = []
        self.workloads = []
        self.full_snapshots = []
        self.restores = []
        self.fingerprint = ""
        self.vm_details_list = []
        self.vms_details = []
        self.floating_ips_list = []
        self.original_fingerprint = ""
        self.vm_list = []
        self.restored_vm_details_list = []
        self.floating_ips_list_after_restore = []
        self.vms_details_after_restore = []
        self.instance_details = []
        self.network_details = []
        volumes = tvaultconf.volumes_parts
        mount_points = ["mount_data_b", "mount_data_c"]
        self.original_fingerprint = self.create_key_pair(tvaultconf.key_pair_name)
	ts=str(datetime.datetime.now()).replace('.','-')
        security_group_id = self.create_security_group("sec_group_{}".format(tvaultconf.security_group_name+ts)," security group {}".format("test_sec"), secgrp_cleanup=True)
        self.add_security_group_rule(parent_group_id = security_group_id, ip_protocol="TCP", from_port = "1", to_port= randint(1, 65535)
)
        self.add_security_group_rule(parent_group_id = security_group_id, ip_protocol="UDP", from_port = "1", to_port= randint(1, 65535)
)
        self.add_security_group_rule(parent_group_id = security_group_id, ip_protocol="TCP", from_port = 22, to_port= 22)
        flavor_id = self.get_flavor_id(tvaultconf.flavor_name)
        if(flavor_id == 0):
            flavor_id = self.create_flavor(tvaultconf.flavor_name)
        self.original_flavor_conf = self.get_flavor_details(flavor_id)

        for vm in range(0,self.vms_per_workload):
            vm_name = "tempest_test_vm_" + str(vm+1)
            volume_id1 = self.create_volume()
            volume_id2 = self.create_volume()
            vm_id = self.create_vm(vm_name=vm_name ,security_group_id=security_group_id,flavor_id=flavor_id, key_pair=tvaultconf.key_pair_name, vm_cleanup=True)
            self.workload_instances.append(vm_id)
            self.workload_volumes.append(volume_id1)
            self.workload_volumes.append(volume_id2)
            self.attach_volume(volume_id1, vm_id, device=volumes[0])
            self.attach_volume(volume_id2, vm_id, device=volumes[1])

        for id in range(len(self.workload_instances)):
            available_floating_ips = self.get_floating_ips()
            if(len(available_floating_ips) > 0):
                floating_ip = self.get_floating_ips()[0]
            else:
		self.exception = "Floating ips availability"
                raise Exception(self.exception)
            self.floating_ips_list.append(floating_ip)
            self.set_floating_ip(str(floating_ip), self.workload_instances[id])
            ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip))
            self.execute_command_disk_create(ssh, str(floating_ip),volumes,mount_points)
            self.execute_command_disk_mount(ssh, str(floating_ip),volumes,mount_points)
            ssh.close()

        #Fetch instance details before restore
        for id in range(len(self.workload_instances)):
            self.vm_details_list.append(self.get_vm_details(self.workload_instances[id]))
            
        self.vms_details = self.get_vms_details_list(self.vm_details_list)
        LOG.debug("vm details list before backups" + str( self.vm_details_list))
        LOG.debug("vm details dir before backups" + str( self.vms_details))

        #Fill some data on each of the volumes attached
        for floating_ip in self.floating_ips_list:
            ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip))
            for mount_point in mount_points:
                self.addCustomSizedfilesOnLinux(ssh, mount_point, 3)
        	ssh.close()
        #Create workload and trigger full snapshot
        self.workload_id=self.workload_create(self.workload_instances,tvaultconf.parallel)
        self.snapshot_id=self.workload_snapshot(self.workload_id, True)
        self.wait_for_workload_tobe_available(self.workload_id)
        if(self.getSnapshotStatus(self.workload_id, self.snapshot_id) != "available"):
	    self.exception = "Full snapshot failed"
            raise Exception(self.exception)

    except Exception as self.exception:
        LOG.error("Exception" + str(self.exception))


def selective_basic(self):
    try:
        self.exception = ""
        self.total_workloads=1
        self.vms_per_workload=2
        self.volume_size=1
        self.workload_instances = []
        self.workload_volumes = []
        self.workloads = []
        self.full_snapshots = []
        self.restores = []
        self.fingerprint = ""
        self.vm_details_list = []
        self.vms_details = []
        self.original_fingerprint = ""
        self.vm_list = []
        self.restored_vm_details_list = []
        self.vms_details_after_restore = []
        self.instance_details = []
        self.network_details = []
        volumes = tvaultconf.volumes_parts
        self.security_group_id = ""
        self.flavor_id = ""
        self.original_fingerprint = self.create_key_pair(tvaultconf.key_pair_name)
	ts=str(datetime.datetime.now()).replace('.','-')
        self.security_group_id = self.create_security_group("sec_group_{}".format(tvaultconf.security_group_name+ts)," security group {}".format("test_sec"), secgrp_cleanup=True)
        self.add_security_group_rule(parent_group_id = self.security_group_id, ip_protocol="TCP", from_port = "1", to_port= randint(1, 65535)
)
        self.add_security_group_rule(parent_group_id = self.security_group_id, ip_protocol="UDP", from_port = "1", to_port= randint(1, 65535)
)
        self.add_security_group_rule(parent_group_id = self.security_group_id, ip_protocol="TCP", from_port = 22, to_port= 22)
        self.flavor_id = self.get_flavor_id(tvaultconf.flavor_name)
        if(self.flavor_id == 0):
            self.flavor_id = self.create_flavor(tvaultconf.flavor_name)
        self.original_flavor_conf = self.get_flavor_details(self.flavor_id)

        for vm in range(0,self.vms_per_workload):
            vm_name = "tempest_test_vm_" + str(vm+1)
            volume_id1 = self.create_volume()
            volume_id2 = self.create_volume()
            vm_id = self.create_vm(vm_name=vm_name ,security_group_id=self.security_group_id,flavor_id=self.flavor_id, key_pair=tvaultconf.key_pair_name, vm_cleanup=True)
            self.workload_instances.append(vm_id)
            self.workload_volumes.append(volume_id1)
            self.workload_volumes.append(volume_id2)
            self.attach_volume(volume_id1, vm_id, device=volumes[0])
            self.attach_volume(volume_id2, vm_id, device=volumes[1])


        #Fetch instance details before restore
        for id in range(len(self.workload_instances)):
            self.vm_details_list.append(self.get_vm_details(self.workload_instances[id]))
            
        self.vms_details = self.get_vms_details_list(self.vm_details_list)
        LOG.debug("vm details list before backups" + str( self.vm_details_list))
        LOG.debug("vm details dir before backups" + str( self.vms_details))

        #Create workload and trigger full snapshot
        self.workload_id=self.workload_create(self.workload_instances,tvaultconf.parallel)
        self.snapshot_id=self.workload_snapshot(self.workload_id, True)
        self.wait_for_workload_tobe_available(self.workload_id)
        if(self.getSnapshotStatus(self.workload_id, self.snapshot_id) != "available"):
	    self.exception = "Create full snapshot"
            raise Exception(str(self.exception))

    except Exception as self.exception:
        LOG.error("Exception" + str(self.exception))

def filesearch(self):
    try:
	self.exception=""
        self.filecount_in_snapshots = {}
        volumes = tvaultconf.volumes_parts
        mount_points = ["mount_data_b", "mount_data_c"]
        self.snapshot_ids = []
        self.instances_ids = []
        self.volumes_ids = []
        self.date_from = ""
        self.date_to = ""
        self.total_vms = 2
        self.total_volumes_per_vm = 2

        # Create key_pair and get available floating IP's
        self.create_key_pair(tvaultconf.key_pair_name, keypair_cleanup=False)
        ts = str(datetime.datetime.now()).replace('.','-')
        self.security_group_id = self.create_security_group("sec_group_{}".format(tvaultconf.security_group_name+ts)," security group {}".format("test_sec"), secgrp_cleanup=False)
        self.add_security_group_rule(parent_group_id = self.security_group_id, ip_protocol="TCP", from_port = "1", to_port= randint(1, 65535))
        self.add_security_group_rule(parent_group_id = self.security_group_id, ip_protocol="UDP", from_port = "1", to_port= randint(1, 65535))
        self.add_security_group_rule(parent_group_id = self.security_group_id, ip_protocol="TCP", from_port = 22, to_port= 22)
        floating_ips_list = self.get_floating_ips()   

        # Create two volumes, Launch two instances, Attach volumes to the instances and Assign Floating IP's
        # Partitioning and  formatting and mounting the attached disks
        for i in range(0, self.total_vms):
            vm_name = "Test_Tempest_Vm" + str(i+1)
            j = i + i
            for n in range(0, self.total_volumes_per_vm):
                self.volumes_ids.append(self.create_volume(volume_cleanup=False))
                LOG.debug("Volume-"+ str(n+j+1) +" ID: " + str(self.volumes_ids[n+j]))
            self.instances_ids.append(self.create_vm(vm_cleanup=False, vm_name=vm_name, key_pair=tvaultconf.key_pair_name, security_group_id=self.security_group_id))
            LOG.debug("VM-"+ str(i+1) +" ID: " + str(self.instances_ids[i]))
            self.attach_volume(self.volumes_ids[j], self.instances_ids[i], volumes[0])
            time.sleep(10)
            self.attach_volume(self.volumes_ids[j+1], self.instances_ids[i], volumes[1])
            time.sleep(10)
            LOG.debug("Two Volumes attached")
            self.set_floating_ip(floating_ips_list[i], self.instances_ids[i])
            time.sleep(15)

            self.ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ips_list[i]))
            self.execute_command_disk_create(self.ssh, floating_ips_list[i], volumes, mount_points)
            self.ssh.close()

            self.ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ips_list[i]))
            self.execute_command_disk_mount(self.ssh, floating_ips_list[i], volumes, mount_points)
            self.ssh.close()
                
        # Create workload
        self.wid = self.workload_create(self.instances_ids, tvaultconf.parallel, workload_name=tvaultconf.workload_name, workload_cleanup=False)
        LOG.debug("Workload ID: " + str(self.wid))
        workload_available = self.wait_for_workload_tobe_available(self.wid)
                    
        # Create full snapshot
	self.snapshot_id=self.workload_snapshot(self.wid, True, snapshot_cleanup=False)
        self.wait_for_workload_tobe_available(self.wid)
        if(self.getSnapshotStatus(self.wid, self.snapshot_id) != "available"):
            self.exception = "Create full snapshot"
            raise Exception(str(self.exception)) 

	self.snapshot_ids.append(self.snapshot_id)

        LOG.debug("Snapshot ID-1: " + str(self.snapshot_ids[0]))
        time_now = time.time()
        self.date_from = datetime.datetime.utcfromtimestamp(time_now).strftime("%Y-%m-%dT%H:%M:%S")

        # Add two files to vm1 to path /opt
        self.ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ips_list[0]))
        self.addCustomSizedfilesOnLinux(self.ssh, "//opt", 2)
        self.ssh.close()

        # Create incremental-1 snapshot
	self.snapshot_id=self.workload_snapshot(self.wid, False, snapshot_cleanup=False)
        self.wait_for_workload_tobe_available(self.wid)
        if(self.getSnapshotStatus(self.wid, self.snapshot_id) != "available"):
            self.exception = "Create incremental-1 snapshot"
            raise Exception(str(self.exception))

	self.snapshot_ids.append(self.snapshot_id)
        LOG.debug("Snapshot ID-2: " + str(self.snapshot_ids[1]))    

        # Add two files to vm2 to path /home/ubuntu/mount_data_c
        self.ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ips_list[1]))
        self.addCustomSizedfilesOnLinux(self.ssh, "//home/ubuntu/mount_data_c", 2)
        self.ssh.close()

        # Create incremental-2 snapshot
	self.snapshot_id=self.workload_snapshot(self.wid, False, snapshot_cleanup=False)
        self.wait_for_workload_tobe_available(self.wid)
        if(self.getSnapshotStatus(self.wid, self.snapshot_id) != "available"):
            self.exception = "Create incremental-2 snapshot"
            raise Exception(str(self.exception))

        self.snapshot_ids.append(self.snapshot_id)
        LOG.debug("Snapshot ID-3: " + str(self.snapshot_ids[2]))

        # Add one  file to vm1 to path /home/ubuntu/mount_data_b
        self.ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ips_list[0]))
        self.addCustomSizedfilesOnLinux(self.ssh, "//home/ubuntu/mount_data_b", 1)
        self.ssh.close()

        # Create incremental-3 snapshot
	self.snapshot_id=self.workload_snapshot(self.wid, False, snapshot_cleanup=False)
        self.wait_for_workload_tobe_available(self.wid)
        if(self.getSnapshotStatus(self.wid, self.snapshot_id) != "available"):
            self.exception = "Create incremental-3 snapshot"
            raise Exception(str(self.exception))
        
	self.snapshot_ids.append(self.snapshot_id)
	LOG.debug("Snapshot ID-4: " + str(self.snapshot_ids[3]))
        time_now = time.time()
        self.date_to = datetime.datetime.utcfromtimestamp(time_now).strftime("%Y-%m-%dT%H:%M:%S")

    except Exception as self.exception:
        LOG.error("Exception" + str(self.exception))


def basic_workload(self):
    try:
	self.exception=""
        self.workload_instances = []
            
        #Create volume
        self.volume_id = self.create_volume(volume_cleanup=False)
        LOG.debug("Volume ID: " + str(self.volume_id))

        #Launch instance
        self.vm_id = self.create_vm(vm_cleanup=False)
        LOG.debug("VM ID: " + str(self.vm_id))
        
        #Attach volume to the instance
        self.attach_volume(self.volume_id, self.vm_id)
        LOG.debug("Volume attached")

        #Create workload
        self.workload_instances.append(self.vm_id)
        self.wid = self.workload_create(self.workload_instances, tvaultconf.parallel, workload_name=tvaultconf.workload_name, workload_cleanup=False)
        LOG.debug("Workload ID: " + str(self.wid))

    except Exception as self.exception:
        LOG.error("Exception" + str(self.exception))

def bootfromvol_workload(self):
    try:
	self.exception=""
        self.total_workloads=1
        self.vms_per_workload=1
        self.workload_instances = []
        self.workload_volumes = []

        for vm in range(0,self.vms_per_workload):
             self.volume_id = self.create_volume(size=tvaultconf.bootfromvol_vol_size, image_id=CONF.compute.image_ref, volume_cleanup=False)
             self.workload_volumes.append(self.volume_id)
             self.set_volume_as_bootable(self.volume_id)
             self.block_mapping_details = [{ "source_type": "volume", 
        		   "delete_on_termination": "false",
        		   "boot_index": 0,
        		   "uuid": self.volume_id,
        		   "destination_type": "volume"}]
             self.vm_id = self.create_vm(image_id="", block_mapping_data=self.block_mapping_details, vm_cleanup=False)
             self.workload_instances.append(self.vm_id)

        #Create workload
        self.workload_id=self.workload_create(self.workload_instances,tvaultconf.parallel, workload_cleanup=False)
        if (self.wait_for_workload_tobe_available(self.workload_id) == False):
            reporting.add_test_step("Create_Workload", tvaultconf.FAIL)
            raise Exception("Workload creation failed")
        self.workload_status = self.getWorkloadStatus(self.workload_id)

    except Exception as self.exception:
        LOG.error("Exception" + str(self.exception))

def config_workload(self):
    self.config_user_create()    

def config_backup(self):
    self.config_user_create()
    # for config backup configuration, yaml_file creation
    added_dir = {tvaultconf.additional_dir.keys()[0]:{'config_dir':tvaultconf.additional_dir.values()[0]}}
    self.create_config_backup_yaml(added_dir = added_dir)

    # config backup configuration with CLI command
    config_workload_command = command_argument_string.config_workload_configure + " --config-file yaml_file.yaml --authorized-key config_backup_pvk "

    LOG.debug("config workload configure cli command: " + str(config_workload_command))

    rc = cli_parser.cli_returncode(config_workload_command)
    if rc != 0:
        LOG.debug("Triggering config_workload_configure command via CLI FAIL")
        raise Exception("Command did not execute correctly")
    else:
        LOG.debug("Triggering config_workload_configure command via CLI PASS")
        LOG.debug("Command executed correctly")

'''
boot from volume 2 vms, 2 volumes attached to each, 3 files added to each of the volumes, md5 sum for each vm, 1 workload, full snapshot and incremental snapshot
'''
def bootfromvol_workload_medium(self):
    try:
        self.exception = ""
        self.total_workloads=1
        self.vms_per_workload=2
        self.workload_instances = []
        self.workload_volumes = []
        self.floating_ips_list = []
        volumes = tvaultconf.volumes_parts
        mount_points = ["mount_data_b", "mount_data_c"]

        self.original_fingerprint = self.create_key_pair(tvaultconf.key_pair_name,keypair_cleanup=False)
	ts = str(datetime.datetime.now()).replace('.','-')

        self.security_group_id = self.create_security_group(tvaultconf.security_group_name+ts,"tempest_sample_description", secgrp_cleanup=False)
        self.add_security_group_rule(parent_group_id = self.security_group_id, ip_protocol="TCP", from_port = "1", to_port= randint(1, 65535))
        self.add_security_group_rule(parent_group_id = self.security_group_id, ip_protocol="UDP", from_port = "1", to_port= randint(1, 65535))
        self.add_security_group_rule(parent_group_id = self.security_group_id, ip_protocol="TCP", from_port = 22, to_port= 22)
        LOG.debug("security group id" + str(self.security_group_id))

        self.flavor_id = self.get_flavor_id(tvaultconf.flavor_name)
        if(self.flavor_id == 0):
            self.flavor_id = self.create_flavor(tvaultconf.flavor_name,flavor_cleanup=False)
        self.original_flavor_conf = self.get_flavor_details(self.flavor_id)

        for vm in range(0,self.vms_per_workload):
            self.volume_id_1 = self.create_volume(size=tvaultconf.bootfromvol_vol_size, image_id=CONF.compute.image_ref, volume_cleanup=False)
            self.volume_id_2 = self.create_volume(volume_cleanup=False)
            self.volume_id_3 = self.create_volume(volume_cleanup=False)
            self.workload_volumes.append(self.volume_id_1)
            self.workload_volumes.append(self.volume_id_2)
            self.workload_volumes.append(self.volume_id_3)
            self.set_volume_as_bootable(self.volume_id_1)
            self.block_mapping_details = [{ "source_type": "volume",
                       "delete_on_termination": "false",
                       "boot_index": 0,
                       "uuid": self.volume_id_1,
                       "destination_type": "volume"}]

            self.vm_id = self.create_vm(image_id="",security_group_id=self.security_group_id,flavor_id=self.flavor_id, key_pair=tvaultconf.key_pair_name, block_mapping_data=self.block_mapping_details, vm_cleanup=False)
            self.attach_volume(self.volume_id_2, self.vm_id, device=volumes[0])
            self.attach_volume(self.volume_id_3, self.vm_id, device=volumes[1])
            self.workload_instances.append(self.vm_id)

        for id in range(len(self.workload_instances)):
            available_floating_ips = self.get_floating_ips()
            if(len(available_floating_ips) > 0):
                floating_ip = self.get_floating_ips()[0]
            else:
	        self.exception = "Floating ips availability"
                raise Exception(self.exception)
            self.floating_ips_list.append(floating_ip)
            self.set_floating_ip(str(floating_ip), self.workload_instances[id])

        tree = lambda: collections.defaultdict(tree)
        self.md5sums_dir_before = tree()

        for floating_ip in self.floating_ips_list:
            ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip))
            self.execute_command_disk_create(ssh, str(floating_ip),volumes,mount_points)
            #self.channel.close()
            ssh.close()

            ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip))
            self.execute_command_disk_mount(ssh, str(floating_ip),volumes,mount_points)
            #self.channel.close()
            ssh.close()

            ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip))
            self.addCustomSizedfilesOnLinux(ssh, mount_points[0], 1)
            ssh.close()

            ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip))
            self.addCustomSizedfilesOnLinux(ssh, mount_points[1], 1)
            ssh.close()

            for mount_point in mount_points:
                ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip))
                self.md5sums_dir_before[str(floating_ip)][str(mount_point)] = self.calculatemmd5checksum(ssh, mount_point)
                ssh.close()

        LOG.debug("md5sums_dir_before" + str(self.md5sums_dir_before))

        self.vm_details_list = []

        #Fetch instance details before restore
        for id in range(len(self.workload_instances)):
            self.vm_details_list.append(self.get_vm_details(self.workload_instances[id]))

        self.vms_details = self.get_vms_details_list(self.vm_details_list)
        LOG.debug("vm details list before backups" + str( self.vm_details_list))
        LOG.debug("vm details dir before backups" + str( self.vms_details))

        #Create workload
        self.workload_id=self.workload_create(self.workload_instances,tvaultconf.parallel, workload_cleanup=False)
        if (self.wait_for_workload_tobe_available(self.workload_id) == False):
	    self.exception = "Create_Workload"
            raise Exception(self.exception)
        self.workload_status = self.getWorkloadStatus(self.workload_id)

        self.snapshot_ids = []

        # Create full snapshot
        self.snapshot_ids.append(self.workload_snapshot(self.workload_id, True, snapshot_cleanup=False))
        LOG.debug("Full Snapshot_id: " + str(self.snapshot_ids[0]))
        #Wait till snapshot is complete
        self.wait_for_snapshot_tobe_available(self.workload_id, self.snapshot_ids[0])

        # Create incr snapshot
        self.snapshot_ids.append(self.workload_snapshot(self.workload_id, False, snapshot_cleanup=False))
        LOG.debug("Incr Snapshot_id: " + str(self.snapshot_ids[1]))
        #Wait till snapshot is complete
        self.wait_for_snapshot_tobe_available(self.workload_id, self.snapshot_ids[1])

    except Exception as self.exception:
        LOG.error("Exception" + str(self.exception))

def nested_security(self):
    try:
	self.exception = ""
        self.security_group_list = []
        #  create security group 1-5
        n = 5
	LOG.debug("create initial security groups")
	ts = "".join(str(datetime.datetime.now()).replace('.','-').split())
	self.security_group_id = self.create_security_group(tvaultconf.security_group_name+ts,"tempest_sample_description", secgrp_cleanup=False)
        self.add_security_group_rule(parent_group_id = self.security_group_id, ip_protocol="TCP", from_port = "1", to_port= randint(1, 65535))
        self.add_security_group_rule(parent_group_id = self.security_group_id, ip_protocol="UDP", from_port = "1", to_port= randint(1, 65535))
        self.add_security_group_rule(parent_group_id = self.security_group_id, ip_protocol="TCP", from_port = 22, to_port= 22)
        LOG.debug("security group id" + str(self.security_group_id))
	self.security_group_list.append(self.security_group_id)

    except Exception as self.exception:
        LOG.error("Exception" + str(self.exception))
