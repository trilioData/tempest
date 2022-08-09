import os
import sys

from oslo_log import log as logging

from tempest import config
from tempest import reporting
from tempest import test
from tempest import tvaultconf
from tempest.api.workloadmgr import base
from tempest.lib import decorators

sys.path.append(os.getcwd())

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    instances_ids = []
    snapshot_ids = []
    date_from = ""
    date_to = ""
    wid = ""
    security_group_id = ""
    volumes_ids = []

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()

    @test.pre_req({'type': 'filesearch'})
    @decorators.attr(type='workloadmgr_api')
    def test_1_filesearch_default_parameters(self):
        reporting.add_test_script(str(__name__) + "_default_parameters")
        try:
            if self.exception != "":
                LOG.debug("pre req failed")
                reporting.add_test_step(str(self.exception), tvaultconf.FAIL)
                raise Exception(str(self.exception))
            LOG.debug("pre req completed")

            global instances_ids
            global snapshot_ids
            global date_from
            global date_to
            global wid
            global security_group_id
            global volumes_ids
            instances_ids = self.instances_ids
            snapshot_ids = self.snapshot_ids
            date_from = self.date_from
            date_to = self.date_to
            wid = self.wid
            volumes_ids = self.volumes_ids
            security_group_id = self.security_group_id
            # Run Filesearch on vm-1
            vmid_to_search = instances_ids[0]
            filepath_to_search = "/opt/File_1"

            LOG.debug(
                "global parameters: {0} {1} {2} {3} {4} {5} {6}".format(
                    str(instances_ids),
                    str(snapshot_ids),
                    str(date_from),
                    str(date_to),
                    str(wid),
                    str(volumes_ids),
                    str(security_group_id)))
            filecount_in_snapshots = {
                snapshot_ids[0]: 0,
                snapshot_ids[1]: 1,
                snapshot_ids[2]: 1,
                snapshot_ids[3]: 1}
            filesearch_id = self.filepath_search(
                vmid_to_search, filepath_to_search)
            filesearch_status = self.getSearchStatus(filesearch_id)
            if filesearch_status == 'error':
                raise Exception("File search failed")
            snapshot_wise_filecount = self.verifyFilepath_Search(
                filesearch_id, filepath_to_search)
            for snapshot_id in filecount_in_snapshots.keys():
                if snapshot_wise_filecount[snapshot_id] == filecount_in_snapshots[snapshot_id]:
                    filesearch_status = True
                else:
                    filesearch_status = False
                    LOG.debug("Filepath Search default_parameters unsuccessful")
                    reporting.add_test_step(
                        "Verification of Filepath serach default_parameters",
                        tvaultconf.FAIL)
                    raise Exception(
                        "Filesearch default_parameters does not execute correctly")

            if filesearch_status:
                LOG.debug("Filepath_Search default_parameters successful")
                reporting.add_test_step(
                    "Verification of Filepath serach default_parameters",
                    tvaultconf.PASS)
                reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_2_filesearch_snapshotids(self):
        reporting.add_test_script(str(__name__) + "_snapshotids")
        try:
            global instances_ids
            global snapshot_ids
            global date_from
            global date_to
            global wid
            global security_group_id
            global volumes_ids

            LOG.debug(
                "gloabal parameters: {0} {1} {2} {3} {4} {5} {6}".format(
                    str(instances_ids),
                    str(snapshot_ids),
                    str(date_from),
                    str(date_to),
                    str(wid),
                    str(volumes_ids),
                    str(security_group_id)))

            # Run Filesearch on vm-1 with snapshot IDs
            vmid_to_search = instances_ids[0]
            filepath_to_search = "/File_1"
            snapshot_ids_tosearch = snapshot_ids[2]
            filecount_in_snapshots = {
                snapshot_ids[0]: 0,
                snapshot_ids[1]: 0,
                snapshot_ids[2]: 0,
                snapshot_ids[3]: 1}
            filesearch_id = self.filepath_search(
                vmid_to_search, filepath_to_search, snapshot_ids_tosearch)
            filesearch_status = self.getSearchStatus(filesearch_id)
            if filesearch_status == 'error':
                raise Exception("File search failed")
            snapshot_wise_filecount = self.verifyFilepath_Search(
                filesearch_id, filepath_to_search)
            for snapshot_id in snapshot_wise_filecount.keys():
                if filecount_in_snapshots[snapshot_id] == snapshot_wise_filecount[snapshot_id] and snapshot_id in snapshot_ids[2]:
                    filesearch_status = True
                else:
                    filesearch_status = False
                    LOG.debug("Filepath Search with snapshotids unsuccessful")
                    reporting.add_test_step(
                        "Verification of Filepath serach with snapshotids", tvaultconf.FAIL)
                    raise Exception(
                        "Filesearch with snapshotids does not execute correctly")

            if filesearch_status:
                LOG.debug("Filepath_Search with snapshotids successful")
                reporting.add_test_step(
                    "Verification of Filepath serach with snapshotids",
                    tvaultconf.PASS)
                reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_3_filesearch_firsttwosnapshots(self):
        reporting.add_test_script(str(__name__) + "_firsttwosnapshots")
        try:
            global instances_ids
            global snapshot_ids
            # Run Filesearch on vm-1 with latest snapshots
            vmid_to_search = instances_ids[0]
            filepath_to_search = "/File_1"
            snapshot_ids_tosearch = []
            start_snapshot = 2
            end_snapshot = 0

            filecount_in_snapshots = {
                snapshot_ids[0]: 0,
                snapshot_ids[1]: 0,
                snapshot_ids[2]: 0,
                snapshot_ids[3]: 1}
            filesearch_id = self.filepath_search(
                vmid_to_search,
                filepath_to_search,
                snapshot_ids_tosearch,
                start_snapshot,
                end_snapshot)
            filesearch_status = self.getSearchStatus(filesearch_id)
            if filesearch_status == 'error':
                raise Exception("File search failed")
            snapshot_wise_filecount = self.verifyFilepath_Search(
                filesearch_id, filepath_to_search)
            for snapshot_id in snapshot_wise_filecount.keys():
                if filecount_in_snapshots[snapshot_id] == snapshot_wise_filecount[snapshot_id] and snapshot_id in snapshot_ids[:2]:
                    filesearch_status = True
                else:
                    filesearch_status = False
                    LOG.debug(
                        "Filepath Search for firsttwosnapshots unsuccessful")
                    reporting.add_test_step(
                        "Verification of Filepath serach for firsttwosnapshots",
                        tvaultconf.FAIL)
                    raise Exception(
                        "Filesearch for firsttwosnapshots does not execute correctly")

            if filesearch_status:
                LOG.debug("Filepath_Search for firsttwosnapshots successful")
                reporting.add_test_step(
                    "Verification of Filepath serach for firsttwosnapshots",
                    tvaultconf.PASS)
                reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_4_filesearch_latesttwosnapshots(self):
        reporting.add_test_script(str(__name__) + "_latesttwosnapshots")
        try:
            global instances_ids
            global snapshot_ids
            # Run Filesearch on vm-1 with latest snapshots
            vmid_to_search = instances_ids[0]
            filepath_to_search = "/File_1"
            snapshot_ids_tosearch = []
            start_snapshot = 0
            end_snapshot = 2

            filecount_in_snapshots = {
                snapshot_ids[0]: 0,
                snapshot_ids[1]: 0,
                snapshot_ids[2]: 0,
                snapshot_ids[3]: 1}
            filesearch_id = self.filepath_search(
                vmid_to_search,
                filepath_to_search,
                snapshot_ids_tosearch,
                start_snapshot,
                end_snapshot)
            filesearch_status = self.getSearchStatus(filesearch_id)
            if filesearch_status == 'error':
                raise Exception("File search failed")
            snapshot_wise_filecount = self.verifyFilepath_Search(
                filesearch_id, filepath_to_search)
            for snapshot_id in snapshot_wise_filecount.keys():
                if filecount_in_snapshots[snapshot_id] == snapshot_wise_filecount[snapshot_id] and snapshot_id in snapshot_ids[2:]:
                    filesearch_status = True
                else:
                    filesearch_status = False
                    LOG.debug(
                        "Filepath Search for latesttwosnapshots unsuccessful")
                    reporting.add_test_step(
                        "Verification of Filepath serach for latesttwosnapshots",
                        tvaultconf.FAIL)
                    raise Exception(
                        "Filesearch for latesttwosnapshots does not execute correctly")

            if filesearch_status:
                LOG.debug("Filepath_Search for latesttwosnapshots successful")
                reporting.add_test_step(
                    "Verification of Filepath serach for latesttwosnapshots",
                    tvaultconf.PASS)
                reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_5_filesearch_daterange(self):
        reporting.add_test_script(str(__name__) + "_daterange")
        try:
            global instances_ids
            global snapshot_ids
            global date_from
            global date_to
            # Run Filesearch on vm-1 with latest snapshots
            vmid_to_search = instances_ids[0]
            filepath_to_search = "/File_1"
            snapshot_ids_tosearch = []
            start_snapshot = 0
            end_snapshot = 0

            filecount_in_snapshots = {
                snapshot_ids[0]: 0,
                snapshot_ids[1]: 0,
                snapshot_ids[2]: 0,
                snapshot_ids[3]: 1}
            filesearch_id = self.filepath_search(
                vmid_to_search,
                filepath_to_search,
                snapshot_ids_tosearch,
                start_snapshot,
                end_snapshot,
                date_from,
                date_to)
            filesearch_status = self.getSearchStatus(filesearch_id)
            if filesearch_status == 'error':
                raise Exception("File search failed")
            snapshot_wise_filecount = self.verifyFilepath_Search(
                filesearch_id, filepath_to_search)
            for snapshot_id in snapshot_wise_filecount.keys():
                if filecount_in_snapshots[snapshot_id] == snapshot_wise_filecount[snapshot_id] and snapshot_id in snapshot_ids[1:]:
                    filesearch_status = True
                else:
                    filesearch_status = False
                    LOG.debug("Filepath Search with daterange unsuccessful")
                    reporting.add_test_step(
                        "Verification of Filepath serach with daterange", tvaultconf.FAIL)
                    raise Exception(
                        "Filesearch with daterange does not execute correctly")

            if filesearch_status:
                LOG.debug("Filepath_Search successful with daterange")
                reporting.add_test_step(
                    "Verification of Filepath serach with daterange",
                    tvaultconf.PASS)
                reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_6_filesearch_wildcard_star(self):
        reporting.add_test_script(str(__name__) + "_wildcard_star")
        try:
            global instances_ids
            global snapshot_ids
            # Run Filesearch on vm-2
            vmid_to_search = instances_ids[1]
            filepath_to_search = "/File*"
            filecount_in_snapshots = {
                snapshot_ids[0]: 0,
                snapshot_ids[1]: 0,
                snapshot_ids[2]: 2,
                snapshot_ids[3]: 2}
            filesearch_id = self.filepath_search(
                vmid_to_search, filepath_to_search)
            filesearch_status = self.getSearchStatus(filesearch_id)
            if filesearch_status == 'error':
                raise Exception("File search failed")
            snapshot_wise_filecount = self.verifyFilepath_Search(
                filesearch_id, filepath_to_search)
            for snapshot_id in filecount_in_snapshots.keys():
                if snapshot_wise_filecount[snapshot_id] == filecount_in_snapshots[snapshot_id]:
                    filesearch_status = True
                else:
                    filesearch_status = False
                    LOG.debug("Filepath Search with wildcard_star unsuccessful")
                    reporting.add_test_step(
                        "Verification of Filepath serach with wildcard_star",
                        tvaultconf.FAIL)
                    raise Exception(
                        "Filesearch wildcard_star does not execute correctly")

            if filesearch_status:
                LOG.debug("Filepath_Search with wildcard_star successful")
                reporting.add_test_step(
                    "Verification of Filepath serach with wildcard_star",
                    tvaultconf.PASS)
                reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_7_filesearch_wildcards_questionmark(self):
        reporting.add_test_script(str(__name__) + "_wildcards_questionmark")
        try:
            global instances_ids
            global snapshot_ids
            global wid
            global security_group_id
            global volumes_ids
            # Run Filesearch on vm-1
            vmid_to_search = instances_ids[0]
            filepath_to_search = "/opt/File_?"
            filecount_in_snapshots = {
                snapshot_ids[0]: 0,
                snapshot_ids[1]: 2,
                snapshot_ids[2]: 2,
                snapshot_ids[3]: 2}
            filesearch_id = self.filepath_search(
                vmid_to_search, filepath_to_search)
            filesearch_status = self.getSearchStatus(filesearch_id)
            if filesearch_status == 'error':
                raise Exception("File search failed")
            snapshot_wise_filecount = self.verifyFilepath_Search(
                filesearch_id, filepath_to_search)
            for snapshot_id in filecount_in_snapshots.keys():
                if snapshot_wise_filecount[snapshot_id] == filecount_in_snapshots[snapshot_id]:
                    filesearch_status = True
                else:
                    filesearch_status = False
                    LOG.debug(
                        "Filepath Search with wildcards_questionmark unsuccessful")
                    reporting.add_test_step(
                        "Verification of Filepath serach with wildcards_questionmark",
                        tvaultconf.FAIL)
                    raise Exception(
                        "Filesearch with wildcards_questionmark does not execute correctly")

            if filesearch_status:
                LOG.debug(
                    "Filepath_Search with wildcards_questionmark successful")
                reporting.add_test_step(
                    "Verification of Filepath serach with wildcards_questionmark",
                    tvaultconf.PASS)

            # Cleanup
            # Delete all snapshots
            for snapshot_id in snapshot_ids:
                self.snapshot_delete(wid, snapshot_id)

            # Delete workload
            self.workload_delete(wid)

            # Delete VMs
            for instance_id in instances_ids:
                self.delete_vm(instance_id)

            # Delete volumes
            for volume_id in volumes_ids:
                self.delete_volume(volume_id)

            # Delete security group
            self.delete_security_group(security_group_id)

            # Delete key pair
            self.delete_key_pair(tvaultconf.key_pair_name)

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
