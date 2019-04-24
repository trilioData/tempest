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

LOG = logging.getLogger(__name__)
CONF = config.CONF

class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    instances_ids = []
    snapshot_ids = []    
    wid = ""
    security_group_id = ""
    volumes_ids = []

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        cls.client = cls.os.wlm_client

    @test.pre_req({'type':'snapshot_mount'})
    @test.attr(type='smoke')
    @test.idempotent_id('90dfa684-171c-40c7-a195-df53671bec4b')
    def test_1_filesearch_default_parameters(self):
	reporting.add_test_script(str(__name__) + "_full_snasphot")
	try:
	    if self.exception != "":
                LOG.debug("pre req failed")
                reporting.add_test_step(str(self.exception), tvaultconf.FAIL)
                raise Exception (str(self.exception))
            LOG.debug("pre req completed")

	    global instances_ids
	    global snapshot_ids 
	    global wid
	    global security_group_id
	    global volumes_ids
            global fvm_id
            global floating_ips_list
	    instances_ids = self.instances_ids
            snapshot_ids = self.snapshot_ids	  
	    wid = self.wid
	    volumes_ids = self.volumes_ids
            security_group_id = self.security_group_id
	    fvm_id = self.fvm_id
	    full_snapshot_id = snapshot_ids[0]
	    floating_ips_list = self.floating_ips_list

	    LOG.debug("mount snasphot of a full snapshot")
            is_mounted = self.mount_snapshot(wid, full_snapshot_id, fvm_id)
            LOG.debug("VALUE OF is_mounted: " + str(is_mounted))
            if is_mounted == True:
                LOG.debug(" mount snapshot with full snapshot is  successful")
                reporting.add_test_step("Verification of mount snapshot with full snapshot", tvaultconf.PASS)
                reporting.test_case_to_write()
            else:
                LOG.debug("mount snapshot with full snapshot is unsuccessful")
                reporting.add_test_step("Verification of mount snapshot with full snapshot", tvaultconf.FAIL)
                raise Exception ("Snapshot mount with full_snapshot  does not execute correctly")
            
            LOG.debug("validate that snapshot is mounted on FVM")
            self.ssh = self.SshRemoteMachineConnectionWithRSAKey(str(floating_ips_list[1]))
            output_list = self.validate_snasphot_mount(self.ssh)
            self.ssh.close()
            
            for i in output_list:
                if '/home/ubuntu/mount_data_b' in i:
                   LOG.debug("connect to fvm and check mountpoint is mounted on FVM instance")
                   reporting.add_test_step("Verify that mountpoint mounted is shown on FVM instance", tvaultconf.PASS)
                   reporting.test_case_to_write()
                else:
                   LOG.debug("mount snapshot with full snapshot is unsuccessful on FVM")
                   reporting.add_test_step("Verify that  mountpoint mounted is shown on FVM instance", tvaultconf.FAIL)
                   raise Exception ("mountpoint is not showing on FVM instance")
                if 'File_1.txt' in i:
                   LOG.debug("check that file is exist on mounted snapshot")
                   reporting.add_test_step("Verification of file exist on moutned snapshot", tvaultconf.PASS)
                   reporting.test_case_to_write()
                else:
                   LOG.debug("file does not found on FVM instacne")
                   reporting.add_test_step("Verification of file exist on moutned snapshot")
		   raise Exception ("file does not found on FVM instacne")
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
