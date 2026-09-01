from oslo_log import log as logging

from tempest import config
from tempest import reporting
from tempest import tvaultconf
from tempest.api.workloadmgr import base
from tempest.lib import decorators
from tempest.util import query_data

LOG = logging.getLogger(__name__)
CONF = config.CONF


class DMSTargetIsolationTest(base.BaseWorkloadmgrTest):
    """
    TC-DMS-05: Mounts on two different backup targets (one NFS, one S3)
    on the same node are tracked and torn down independently - mounting
    or unmounting one target must not disturb the other target's mount
    or ledger references.

    Like TC-DMS-04, this drives trilio-dms-cli and the
    backup_target_mount_ledger table directly with synthetic job_ids
    rather than through real snapshot/restore jobs - it's exercising
    DMS's own per-target mount bookkeeping, which two real jobs racing
    against each other couldn't reliably isolate as a repeatable test.
    No VM is created; get_enabled_compute_node() reads a real node
    hostname straight from Nova's hypervisor list, since none of this
    needs any actual backup activity.

    Requires both an NFS and an S3 backup target to be configured on
    the environment (the same requirement TC-DMS-04's two variants
    already have individually).
    """
    credentials = ['primary']

    @decorators.attr(type='workloadmgr_api')
    def test_dms_nfs_and_s3_targets_mounted_and_unmounted_independently(self):
        reporting.add_test_script(str(__name__) + "_target_isolation_api")
        try:
            nfs_targets = [b for b in self.listBackupTargets()
                          if b['type'] == 'nfs']
            s3_targets = [b for b in self.listBackupTargets()
                         if b['type'] == 's3']
            if not nfs_targets:
                raise Exception(
                    "No NFS backup target configured on this environment")
            if not s3_targets:
                raise Exception(
                    "No S3 backup target configured on this environment")
            nfs_target = nfs_targets[0]
            s3_target = s3_targets[0]
            LOG.debug(f"NFS target under test: {nfs_target['id']}")
            LOG.debug(f"S3 target under test: {s3_target['id']}")

            token = self.get_os_token(admin=True)
            node_host = self.get_enabled_compute_node()
            LOG.debug(f"Using node: {node_host}")

            nfs_job_id = tvaultconf.dms_mount_job_id
            self.increment_dms_mount_job_id()
            s3_job_id = tvaultconf.dms_mount_job_id
            self.increment_dms_mount_job_id()
            nfs_mount_path = nfs_target['filesystem_export_mount_path']
            s3_mount_path = s3_target['filesystem_export_mount_path']

            # Mount NFS first.
            out_nfs_mount = self.run_dms_cli(
                node_host, "mount", nfs_job_id, nfs_target['id'], 'nfs',
                nfs_mount_path,
                filesystem_export=nfs_target['filesystem_export'])
            nfs_mounted, _ = self.get_dms_mount_state(
                node_host, nfs_mount_path, 'nfs')
            if "new physical mount" in out_nfs_mount and nfs_mounted:
                reporting.add_test_step(
                    "Verify NFS target mounts independently",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify NFS target mounts independently",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # Mount S3 on the same node - must not disturb the NFS mount.
            out_s3_mount = self.run_dms_cli(
                node_host, "mount", s3_job_id, s3_target['id'], 's3',
                s3_mount_path,
                filesystem_export=s3_target['filesystem_export'],
                secret_ref=s3_target['secret_ref'], token=token)
            s3_mounted, s3_running = self.get_dms_mount_state(
                node_host, s3_mount_path, 's3')
            nfs_still_mounted, _ = self.get_dms_mount_state(
                node_host, nfs_mount_path, 'nfs')
            if ("new physical mount" in out_s3_mount and s3_mounted
                    and s3_running and nfs_still_mounted):
                reporting.add_test_step(
                    "Verify S3 target mounts independently without "
                    "disturbing the existing NFS mount", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify S3 target mounts independently without "
                    "disturbing the existing NFS mount", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            nfs_ledger_count = query_data.get_db_rows_count(
                "backup_target_mount_ledger", "jobid", str(nfs_job_id))
            s3_ledger_count = query_data.get_db_rows_count(
                "backup_target_mount_ledger", "jobid", str(s3_job_id))
            if nfs_ledger_count == 1 and s3_ledger_count == 1:
                reporting.add_test_step(
                    "Verify each target has its own independent ledger "
                    "reference", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify each target has its own independent ledger "
                    "reference", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # Unmount S3 - NFS must remain untouched.
            out_s3_unmount = self.run_dms_cli(
                node_host, "unmount", s3_job_id, s3_target['id'], 's3',
                s3_mount_path, filesystem_export=s3_target['filesystem_export'])
            s3_mounted_after, _ = self.get_dms_mount_state(
                node_host, s3_mount_path, 's3')
            nfs_mounted_after_s3_unmount, _ = self.get_dms_mount_state(
                node_host, nfs_mount_path, 'nfs')
            nfs_ledger_after_s3_unmount = query_data.get_db_rows_count(
                "backup_target_mount_ledger", "jobid", str(nfs_job_id))
            if ("physically unmounted" in out_s3_unmount
                    and not s3_mounted_after
                    and nfs_mounted_after_s3_unmount
                    and nfs_ledger_after_s3_unmount == 1):
                reporting.add_test_step(
                    "Verify unmounting S3 tears down only the S3 mount, "
                    "leaving NFS's mount and ledger reference untouched",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify unmounting S3 tears down only the S3 mount, "
                    "leaving NFS's mount and ledger reference untouched",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # Finally unmount NFS too.
            out_nfs_unmount = self.run_dms_cli(
                node_host, "unmount", nfs_job_id, nfs_target['id'], 'nfs',
                nfs_mount_path,
                filesystem_export=nfs_target['filesystem_export'])
            nfs_mounted_final, _ = self.get_dms_mount_state(
                node_host, nfs_mount_path, 'nfs')
            nfs_ledger_final = query_data.get_db_rows_count(
                "backup_target_mount_ledger", "jobid", str(nfs_job_id))
            if ("physically unmounted" in out_nfs_unmount
                    and not nfs_mounted_final and not nfs_ledger_final):
                reporting.add_test_step(
                    "Verify unmounting NFS tears down its mount cleanly",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify unmounting NFS tears down its mount cleanly",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()
