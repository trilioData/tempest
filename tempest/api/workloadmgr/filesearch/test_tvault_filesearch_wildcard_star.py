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

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
	reporting.add_test_script(str(__name__))

    @test.pre_req({'type':'filesearch'})
    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_tvault_filesearch_wildcards(self):
	try:
	    # Run Filesearch on vm-2
	    vmid_to_search = self.instances_ids[1]
   	    filepath_to_search = "/File*"
	    #filecount_in_snapshots = {self.snapshot_ids[0]: 0, self.snapshot_ids[1] : 0, self.snapshot_ids[2] : 2, self.snapshot_ids[3] : 2}
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


