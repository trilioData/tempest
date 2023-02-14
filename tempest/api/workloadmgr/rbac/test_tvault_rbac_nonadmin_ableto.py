import os
import sys
import time

from oslo_log import log as logging

from tempest import config
from tempest import reporting
from tempest import tvaultconf
from tempest.api.workloadmgr import base
from tempest.lib import decorators
from tempest.util import query_data

sys.path.append(os.getcwd())

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()
        reporting.add_test_script(str(__name__))

    @decorators.attr(type='workloadmgr_cli')
    def test_tvault_rbac_nonadmin_ableto(self):
        try:
            # Use non-admin credentials
            os.environ['OS_USERNAME'] = CONF.identity.nonadmin_user
            os.environ['OS_PASSWORD'] = CONF.identity.nonadmin_password
            self.instances_id = []
            failed = False

            # Create volume, Launch an Instance
            self.volumes_id = self.create_volume(volume_cleanup=False)
            LOG.debug("Volume-1 ID: " + str(self.volumes_id))
            self.instances_id.append(self.create_vm(vm_cleanup=False))
            LOG.debug("VM-1 ID: " + str(self.instances_id[0]))
            self.attach_volume(self.volumes_id, self.instances_id[0])
            LOG.debug("Volume attached")


            # Launch recovery instance
            self.recoveryinstances_id = self.create_vm(
                vm_name="file_recovery_manager",
                flavor_id=CONF.compute.flavor_ref_alt,
                user_data=tvaultconf.user_frm_data,
                image_id=list(CONF.compute.fvm_image_ref.values())[0])
            LOG.debug("FRM Instance ID: " + str(self.recoveryinstances_id))

            # Create workload
            self.wid = self.workload_create(
                self.instances_id,
                workload_name=tvaultconf.workload_name)
            LOG.debug("Workload ID: " + str(self.wid))
            workload_available = self.wait_for_workload_tobe_available(
                self.wid)
            if workload_available:
                LOG.debug("Workload created successfully")
                reporting.add_test_step(
                    "Verification of workload creation", tvaultconf.PASS)
                reporting.set_test_script_status(tvaultconf.PASS)
            else:
                LOG.debug("workload creation unsuccessful")
                reporting.add_test_step(
                    "Verification of workload creation", tvaultconf.FAIL)
                raise Exception(
                    "RBAC policy fails for workload creation by non-admin user")

            # Create full snapshot
            self.snapshot_id = self.workload_snapshot(self.wid, True)
            LOG.debug("Snapshot ID-1: " + str(self.snapshot_id))
            # Wait till snapshot is complete
            snapshot_status = self.wait_for_snapshot_tobe_available(
                self.wid, self.snapshot_id)
            if snapshot_status == "available":
                LOG.debug("snapshot created successfully")
                reporting.add_test_step(
                    "Verification of snapshot creation", tvaultconf.PASS)
                reporting.set_test_script_status(tvaultconf.PASS)
            else:
                LOG.debug("snapshot creation unsuccessful")
                reporting.add_test_step(
                    "Verification of snapshot creation", tvaultconf.FAIL)
                raise Exception(
                    "RBAC policy fails for snapshot creation by non-admin user")

            # Delete the original instance
            self.delete_vm(self.instances_id[0])
            LOG.debug("Instance deleted successfully")

            # Delete corresponding volume
            self.delete_volume(self.volumes_id)
            LOG.debug("Volume deleted successfully")

            # Create one-click restore
            restore_status = ""
            restore_name = "restore_1"
            restore_id = self.snapshot_restore(
                self.wid, self.snapshot_id, restore_name=restore_name)
            restore_status = query_data.get_snapshot_restore_status(
                restore_name, self.snapshot_id)
            LOG.debug("Snapshot restore status initial: " +
                      str(restore_status))
            while (str(restore_status) != "available" and str(
                restore_status) != "error"):
                time.sleep(10)
                restore_status = query_data.get_snapshot_restore_status(
                    restore_name, self.snapshot_id)
                LOG.debug("Snapshot restore status: " + str(restore_status))
            if (str(restore_status) == "available"):
                LOG.debug("Snapshot Restore successfully completed")
                reporting.add_test_step(
                    "Snapshot one-click restore verification with DB",
                    tvaultconf.PASS)
            else:
                LOG.debug("Snapshot Restore unsuccessful")
                reporting.add_test_step(
                    "Snapshot one-click restore verification with DB",
                    tvaultconf.FAIL)
                failed = True

            # Mount snapshot
            status = self.mount_snapshot(
                self.wid, self.snapshot_id, self.recoveryinstances_id)
            if status:
                LOG.debug("snapshot Mounted successfully")
                reporting.add_test_step(
                    "Verification of snapshot mount", tvaultconf.PASS)
            else:
                LOG.debug("snapshot Mount unsuccessful")
                reporting.add_test_step(
                    "Verification of snapshot mount", tvaultconf.FAIL)
                failed = True

            # Run Filesearch
            vmid_to_search = self.instances_id[0]
            filepath_to_search = "/etc/passwd"
            filecount_in_snapshots = {self.snapshot_id: 1}
            filesearch_id = self.filepath_search(
                vmid_to_search, filepath_to_search)
            try:
                snapshot_wise_filecount = self.verifyFilepath_Search(
                    filesearch_id, filepath_to_search)
                for snapshot_id in filecount_in_snapshots.keys():
                    if snapshot_wise_filecount[snapshot_id] == filecount_in_snapshots[snapshot_id]:
                        filesearch_status = True
                    else:
                        filesearch_status = False
                        LOG.debug("Filepath Search unsuccessful")
                        reporting.add_test_step(
                            "Verification of Filepath search", tvaultconf.FAIL)
                        failed = True

                if filesearch_status:
                    LOG.debug("Filepath_Search successful")
                    reporting.add_test_step(
                        "Verification of Filepath search", tvaultconf.PASS)
            except Exception as e:
                reporting.add_test_step(
                            "Verification of Filepath search", tvaultconf.FAIL)
                failed = True

            if failed:
                reporting.set_test_script_status(tvaultconf.FAIL)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()
