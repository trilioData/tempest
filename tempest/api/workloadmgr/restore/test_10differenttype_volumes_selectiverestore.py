import sys
import os
sys.path.append(os.getcwd())
from tempest.api.workloadmgr import base
from tempest import config
from tempest import test
from oslo_log import log as logging
from tempest import tvaultconf
from tempest import reporting

LOG = logging.getLogger(__name__)
CONF = config.CONF

class RestoreTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(RestoreTest, cls).setup_clients()
        cls.client = cls.os.wlm_client

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_tvault1107_10difftype_volumes_selectiverestore(self):
	reporting.add_test_script(str(__name__))
	try:
	    self.total_volumes = 10
	    self.volumes_ids = []
	    volumes = tvaultconf.volumes_parts
	    self.instances_ids = []
	    self.instance_details = []
            self.network_details = []
	    iscsi = 0
	    ceph = 0

	    # Create five ceph and five lvm volumes and attach to instance
	    for i in range(0, self.total_volumes/2):
		j = i + i 
                self.volumes_ids.append(self.create_volume(volume_type_id=CONF.volume.volume_type_id, volume_cleanup=True))
                LOG.debug("Volumeceph-"+ str(j+1) +" ID: " + str(self.volumes_ids[j]))
                self.volumes_ids.append(self.create_volume(volume_type_id=CONF.volume.volume_type_id_1, volume_cleanup=True))
                LOG.debug("Volumelvm-"+ str(j+2) +" ID: " + str(self.volumes_ids[j+1]))

	    # Create instance
            self.instances_ids.append(self.create_vm(vm_cleanup=True))
	    LOG.debug("Instance ID: " + str(self.instances_ids[0]))

	    # Attach volumes
	    for i in range(len(self.volumes_ids)):
	        self.attach_volume(self.volumes_ids[i], self.instances_ids[0], volumes[i])

	    reporting.add_test_step("One vm with 5 lvm and 5 ceph volumes attached", tvaultconf.PASS)
	    LOG.debug("One vm with 5 lvm and 5 ceph volumes attached successfully")

	    # Create workload with instance
	    self.wid = self.workload_create(self.instances_ids, tvaultconf.parallel, workload_name=tvaultconf.workload_name, workload_cleanup=True)
            LOG.debug("Workload ID: " + str(self.wid))
            workload_available = self.wait_for_workload_tobe_available(self.wid)
            	
	    # Create snapshot
            self.snapshot_id = self.workload_snapshot(self.wid, True, tvaultconf.snapshot_name)
            LOG.debug("Snapshot ID: " + str(self.snapshot_id))
            # Wait till snapshot is complete
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id)

	    # Get network name and subnet information
	    int_net_1_name = self.get_net_name(CONF.network.internal_network_id)
            LOG.debug("int_net_1_name" + str(int_net_1_name))
            int_net_1_subnets = self.get_subnet_id(CONF.network.internal_network_id)
            LOG.debug("int_net_1_subnet" + str(int_net_1_subnets))

	    # Create instance details for restore.json
            for i in range(len(self.instances_ids)):
                vm_name = "tempest_test_vm_"+str(i+1)+"_restored"
                temp_instance_data = { 'id': self.instances_ids[i],
                                       'include': True,
                                       'restore_boot_disk': True,
                                       'name': vm_name,
                                       'vdisks':[]
                                     }
                self.instance_details.append(temp_instance_data)
            LOG.debug("Instance details for restore: " + str(self.instance_details))

            # Create network details for restore.json
            snapshot_network = { 'name': int_net_1_name,
                                 'id': CONF.network.internal_network_id,
                                 'subnet': { 'id': int_net_1_subnets }
                               }
            target_network = { 'name': int_net_1_name,
                               'id': CONF.network.internal_network_id,
                               'subnet': { 'id': int_net_1_subnets }
                             }
            self.network_details = [ { 'snapshot_network': snapshot_network,
                                       'target_network': target_network } ]
            LOG.debug("Network details for restore: " + str(self.network_details))

	    # Trigger selective restore
            self.restore_id=self.snapshot_selective_restore(self.wid, self.snapshot_id, restore_name=tvaultconf.restore_name, instance_details=self.instance_details, 								  network_details=self.network_details)
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id)
            if(self.getRestoreStatus(self.wid, self.snapshot_id, self.restore_id) == "available"):
                reporting.add_test_step("Selective restore", tvaultconf.PASS)
            else:
                reporting.add_test_step("Selective restore", tvaultconf.FAIL)
                raise Exception("Selective restore failed")

            # Fetch instance details after restore
            self.vm_list  =  self.get_restored_vm_list(self.restore_id)
            LOG.debug("Restored vms : " + str (self.vm_list))

	    # Fetch restored volume list attched to restored vm
	    for vm_id in self.vm_list:
		self.volumes_list = self.get_attached_volumes(vm_id)
	    LOG.debug("Volume listtt : " + str (self.volumes_list))

	    # Verify new 5 ceph and 5 lvm volumes created and attached to restored vm
	    for volume_id in self.volumes_list:
		LOG.debug("Volume ID from list : " + str (volume_id))
	        details = self.get_volume_details(volume_id)
	        volume_type = details[u'volume']['volume_type']
		LOG.debug("VOLUME_TYPE :"+ volume_type)
	        if volume_type == "iscsi":
		    iscsi += 1
		elif volume_type == "ceph":
		    ceph += 1
	    if iscsi == ceph == 5:
		reporting.add_test_step("Verify 5 lvm and 5 ceph volumes are created and attached to restored vm", tvaultconf.PASS)
	    else:
	        reporting.add_test_step("Verify 5 lvm and 5 ceph volumes are created and attached to restored vm", tvaultconf.FAIL)

	    reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
	 
	    

