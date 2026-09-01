from oslo_log import log as logging

from tempest import config
from tempest import reporting
from tempest import tvaultconf
from tempest.api.workloadmgr import base
from tempest.lib import decorators
from tempest.util import query_data

LOG = logging.getLogger(__name__)
CONF = config.CONF


class DMSIdempotencyTest(base.BaseWorkloadmgrTest):
    """
    TC-DMS-04: A duplicate DMS mount request for the same
    (jobid, target_id, host) is idempotent at the physical mount level,
    but each call is its own reference in backup_target_mount_ledger.

    Drives trilio-dms-cli and the ledger table directly instead of going
    through a real snapshot/restore job - this is DMS's own internal
    mount-decision logic (jobid + mounted=1 -> reuse), not something a
    real job's indirect mount/unmount timing can reliably exercise, and
    a synthetic job_id keeps this fast and fully isolated from any real
    backup activity.

    NOTE: verified live against a real environment before writing this
    test - a duplicate mount call for the identical job/target/host does
    NOT double the physical mount (server log: "already mounted", CLI:
    "reused existing mount"), but DOES create a second ledger row rather
    than being a no-op there - releasing the physical mount then needs
    one unmount call per mount call (first unmount: CLI reports "physical
    mount retained for other jobs" with 1 reference remaining; only the
    second actually tears it down). This differs from a literal "complete
    no-op, no duplicate rows" idempotency claim - the assertions below
    check the real, evidence-based behavior.

    The NFS and S3 variants below share the identical mount/duplicate/
    ledger/unmount-twice flow via _verify_mount_refcounting() - they only
    differ in which target to resolve and the extra token/secret_ref S3
    needs, so that flow's assertions only need to be right in one place.
    """
    credentials = ['primary']

    def _verify_mount_refcounting(self, node_host, target_id, mount_path,
                                  target_kind, filesystem_export=None,
                                  secret_ref=None, token=None):
        job_id = tvaultconf.dms_mount_job_id
        self.increment_dms_mount_job_id()
        LOG.debug(f"Synthetic job_id under test: {job_id}")

        # First mount - should be a genuinely new physical mount.
        out1 = self.run_dms_cli(node_host, "mount", job_id, target_id,
                                target_kind, mount_path,
                                filesystem_export=filesystem_export,
                                secret_ref=secret_ref, token=token)
        if "new physical mount" in out1:
            reporting.add_test_step(
                "Verify first mount call creates a new physical mount",
                tvaultconf.PASS)
        else:
            reporting.add_test_step(
                "Verify first mount call creates a new physical mount",
                tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        # Duplicate mount for the identical job/target/host.
        out2 = self.run_dms_cli(node_host, "mount", job_id, target_id,
                                target_kind, mount_path,
                                filesystem_export=filesystem_export,
                                secret_ref=secret_ref, token=token)
        if "reused existing mount" in out2:
            reporting.add_test_step(
                "Verify duplicate mount call reuses the physical mount "
                "(no double-mount)", tvaultconf.PASS)
        else:
            reporting.add_test_step(
                "Verify duplicate mount call reuses the physical mount "
                "(no double-mount)", tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        ledger_count = query_data.get_db_rows_count(
            "backup_target_mount_ledger", "jobid", str(job_id))
        LOG.debug(f"Ledger row count for job_id {job_id}: {ledger_count}")
        if ledger_count == 2:
            reporting.add_test_step(
                "Verify each mount call creates its own ledger reference "
                "(2 calls -> 2 rows)", tvaultconf.PASS)
        else:
            reporting.add_test_step(
                "Verify each mount call creates its own ledger reference "
                "(2 calls -> 2 rows)", tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        # First unmount - one reference remains, physical mount must
        # survive. Unmount doesn't need secret_ref/token (confirmed live)
        # but S3 still needs --filesystem-export even though there's no
        # literal filesystem export for S3 - it's the target's
        # bucket/filesystem_export value.
        out3 = self.run_dms_cli(node_host, "unmount", job_id, target_id,
                                target_kind, mount_path,
                                filesystem_export=filesystem_export)
        mounted_after_1, _ = self.get_dms_mount_state(
            node_host, mount_path, target_kind)
        ledger_count_after_1 = query_data.get_db_rows_count(
            "backup_target_mount_ledger", "jobid", str(job_id))
        LOG.debug(f"After first unmount: mounted={mounted_after_1}, "
                 f"ledger_count={ledger_count_after_1}")
        if ("retained for other jobs" in out3 and mounted_after_1
                and ledger_count_after_1 == 1):
            reporting.add_test_step(
                "Verify first unmount releases one reference but keeps "
                "the physical mount (one reference remains)",
                tvaultconf.PASS)
        else:
            reporting.add_test_step(
                "Verify first unmount releases one reference but keeps "
                "the physical mount (one reference remains)",
                tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

        # Second unmount - last reference, physical mount must come down.
        out4 = self.run_dms_cli(node_host, "unmount", job_id, target_id,
                                target_kind, mount_path,
                                filesystem_export=filesystem_export)
        mounted_after_2, _ = self.get_dms_mount_state(
            node_host, mount_path, target_kind)
        ledger_count_after_2 = query_data.get_db_rows_count(
            "backup_target_mount_ledger", "jobid", str(job_id))
        LOG.debug(f"After second unmount: mounted={mounted_after_2}, "
                 f"ledger_count={ledger_count_after_2}")
        if ("physically unmounted" in out4 and not mounted_after_2
                and not ledger_count_after_2):
            reporting.add_test_step(
                "Verify second unmount releases the last reference and "
                "tears down the physical mount", tvaultconf.PASS)
        else:
            reporting.add_test_step(
                "Verify second unmount releases the last reference and "
                "tears down the physical mount", tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)

    @decorators.attr(type='workloadmgr_api')
    def test_dms_nfs_mount_reference_counted_for_duplicate_requests(self):
        reporting.add_test_script(
            str(__name__) + "_nfs_mount_refcount_api")
        try:
            nfs_targets = [b for b in self.listBackupTargets()
                          if b['type'] == 'nfs']
            if not nfs_targets:
                raise Exception(
                    "No NFS backup target configured on this environment")
            target = nfs_targets[0]
            LOG.debug(f"NFS target under test: {target['id']} "
                     f"({target['filesystem_export']})")

            node_host = self.get_enabled_compute_node()
            LOG.debug(f"Using node: {node_host}")

            self._verify_mount_refcounting(
                node_host, target['id'],
                target['filesystem_export_mount_path'], 'nfs',
                filesystem_export=target['filesystem_export'])
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_dms_s3_mount_reference_counted_for_duplicate_requests(self):
        """
        Same flow as the NFS variant above, for the S3 target instead.

        S3 needs two extra things NFS doesn't: a Keystone token (to fetch
        the target's secret from Barbican) and the secret_ref itself. The
        primary test identity (tvaultconf's trilio-*-user) does NOT have
        Barbican access to this secret - confirmed live ("Access denied to
        secret") - only CONF.auth's admin identity does (see
        get_os_token(admin=True)).
        """
        reporting.add_test_script(
            str(__name__) + "_s3_mount_refcount_api")
        try:
            s3_targets = [b for b in self.listBackupTargets()
                         if b['type'] == 's3']
            if not s3_targets:
                raise Exception(
                    "No S3 backup target configured on this environment")
            target = s3_targets[0]
            LOG.debug(f"S3 target under test: {target['id']} "
                     f"({target['filesystem_export']})")

            token = self.get_os_token(admin=True)

            node_host = self.get_enabled_compute_node()
            LOG.debug(f"Using node: {node_host}")

            self._verify_mount_refcounting(
                node_host, target['id'],
                target['filesystem_export_mount_path'], 's3',
                filesystem_export=target['filesystem_export'],
                secret_ref=target['secret_ref'], token=token)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()
