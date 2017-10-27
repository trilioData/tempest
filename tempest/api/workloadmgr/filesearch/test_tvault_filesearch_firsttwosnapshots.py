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
    def test_tvault_filesearch_firsttwosnapshots(self):
	try:
	    # Run Filesearch on vm-1 with latest snapshots
	    vmid_to_search = self.instances_ids[0]
	    filepath_to_search = "/File_1.txt"
	    snapshot_ids_tosearch = []
	    start_snapshot = 2
	    end_snapshot = 0
	    
	    filecount_in_snapshots = {self.snapshot_ids[0] : 0, self.snapshot_ids[1] : 0, self.snapshot_ids[2] : 0, self.snapshot_ids[3] : 1}
	    filesearch_id = self.filepath_search(vmid_to_search, filepath_to_search, snapshot_ids_tosearch, start_snapshot, end_snapshot)
	    snapshot_wise_filecount = self.verifyFilepath_Search(filesearch_id, filepath_to_search)
	    for snapshot_id in snapshot_wise_filecount.keys():
    	        if filecount_in_snapshots[snapshot_id] == snapshot_wise_filecount[snapshot_id] and snapshot_id in self.snapshot_ids[:2]:
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




