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

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()
        cls.client = cls.os.wlm_client
        reporting.add_test_script(str(__name__))
    
    def test_workload_reset(self):
        try:
            reporting.add_test_script(str(__name__))
            ## VM and Workload ###

            vm_id = self.create_vm(vm_cleanup=True)
            LOG.debug("VM ID : "+str(vm_id))

            volume_id = self.create_volume(volume_cleanup=True)
            LOG.debug("Volume ID: " + str(volume_id))
            volumes = tvaultconf.volumes_parts
    
            self.attach_volume(volume_id, vm_id, attach_cleanup=True)
            LOG.debug("Volume attached")
        
            LOG.debug("Sleeping for 40 sec")
            time.sleep(40)
            i=1
            workload_id = self.workload_create([vm_id],tvaultconf.parallel, workload_name="w1", workload_cleanup=True, description='test')
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

            self.created = False

            snapshot_id = self.workload_snapshot(workload_id, True, snapshot_name="Snap1", snapshot_cleanup=True)

            time.sleep(5)
            self.wait_for_workload_tobe_available(workload_id)
            if(self.getSnapshotStatus(workload_id, snapshot_id) == "available"):
                reporting.add_test_step("Create full snapshot-{}".format(i), tvaultconf.PASS)
                LOG.debug("Full snapshot available!!")
            else:
                reporting.add_test_step("Create full snapshot-{}".format(i), tvaultconf.FAIL)
                raise Exception("Snapshot creation failed")

            i+=1
            volsnaps_before = self.get_volume_snapshots(volume_id)

            LOG.debug("\nVolume snapshots after full snapshot : {}\n".format(volsnaps_before))
           
            self.workload_reset(workload_id)

            time.sleep(10)
            volsnaps_after = self.get_volume_snapshots(volume_id) 
            if len(volsnaps_after) == 0:
                pass
            else:
                LOG.debug("Workload reset failed")
                raise Exception("Workload reset failed")
            
            snapshot_id_1 = self.workload_snapshot(workload_id, True, snapshot_name="Snap2", snapshot_cleanup=True)

            time.sleep(5)
            self.wait_for_workload_tobe_available(workload_id)
            if(self.getSnapshotStatus(workload_id, snapshot_id_1) == "available"):
                reporting.add_test_step("Create full snapshot-{}".format(i), tvaultconf.PASS)
                LOG.debug("Full snapshot available!!")
            else:
                reporting.add_test_step("Create full snapshot-{}".format(i), tvaultconf.FAIL)
                raise Exception("Snapshot creation failed")

            isfull = self.getSnapshotDetails(workload_id, snapshot_id_1)['snapshot_type']
            if isfull == "full":
                LOG.debug("Workload reset passed")
                reporting.add_test_step("Workload reset", tvaultconf.PASS)
                reporting.set_test_script_status(tvaultconf.PASS)
            else:
                LOG.debug("Workload reset failed")
                reporting.add_test_step("Workload reset", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
