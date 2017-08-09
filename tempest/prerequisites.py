
from oslo_log import log as logging
LOG = logging.getLogger(__name__)
from tempest import tvaultconf, reporting
def small_workload(self):
    self.workload_instances = []
    LOG.debug("Running prerequisites for : small_workload")
    vms_per_workload = 1
    for vm in range(0,vms_per_workload):
       vm_id = self.create_vm()
       self.workload_instances.append(vm_id)

def inplace(self):
    self.total_workloads=1
    self.vms_per_workload=1
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
    volumes = ["/dev/vdb", "/dev/vdc"]
    mount_points = ["mount_data_b", "mount_data_c"]
    self.original_fingerprint = self.create_key_pair(tvaultconf.key_pair_name)
    self.security_group_details = self.create_security_group(tvaultconf.security_group_name)
    security_group_id = self.security_group_details['security_group']['id']
    LOG.debug("security group rules" + str(self.security_group_details['security_group']['rules']))
    flavor_id = self.get_flavor_id(tvaultconf.flavor_name)
    if(flavor_id == 0):
        flavor_id = self.create_flavor(tvaultconf.flavor_name)
    self.original_flavor_conf = self.get_flavor_details(flavor_id)

    for vm in range(0,self.vms_per_workload):
        vm_name = "tempest_test_vm_" + str(vm+1)
        volume_id1 = self.create_volume(self.volume_size,tvaultconf.volume_type)
        volume_id2 = self.create_volume(self.volume_size,tvaultconf.volume_type)
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
            reporting.add_test_step("Floating ips availability", tvaultconf.FAIL)
            raise Exception("Floating ips not available")
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
    import collections
    for floating_ip in self.floating_ips_list:
        ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ip))
        for mount_point in mount_points:
            self.addCustomSizedfilesOnLinux(ssh, mount_point, 2)
    	ssh.close()
    #Create workload and trigger full snapshot
    self.workload_id=self.workload_create(self.workload_instances,tvaultconf.parallel)
    self.snapshot_id=self.workload_snapshot(self.workload_id, True)
    self.wait_for_workload_tobe_available(self.workload_id)
    if(self.getSnapshotStatus(self.workload_id, self.snapshot_id) != "available"):
        reporting.add_test_step("Create full snapshot", tvaultconf.FAIL)
        raise Exception("Full Snapshot Failed") 
