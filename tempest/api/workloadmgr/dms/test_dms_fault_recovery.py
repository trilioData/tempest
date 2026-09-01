from oslo_log import log as logging

from tempest import config
from tempest import reporting
from tempest import tvaultconf
from tempest.api.workloadmgr import base
from tempest.lib import decorators

LOG = logging.getLogger(__name__)
CONF = config.CONF


class DMSFaultRecoveryTest(base.BaseWorkloadmgrTest):
    """
    TC-DMS-07: DMS detects a dead S3 FUSE process (errno 107 - ENOTCONN)
    and self-heals - a subsequent mount request for the same target
    proceeds transparently, without any manual intervention.

    S3-only: s3vaultfuse is DMS's S3-specific FUSE daemon, NFS has no
    equivalent process to crash. An NFS "stale mount" variant of this
    test was considered but not automated - it would need either real
    control over the NFS server (to trigger a genuine ESTALE the way it
    actually happens in production) or blocking network traffic to it,
    neither of which is available/safe on this shared lab.

    Drives trilio-dms-cli directly (mount/unmount, same pattern as
    TC-DMS-04/05/06) rather than through a real snapshot job. Initially
    tried the real-job route (crash the process mid-job, let the same
    job self-heal), but live testing showed DMS tears the mount and its
    s3vaultfuse process down entirely once a job's reference is
    released - by the time wait_for_snapshot_tobe_available() returns,
    the PID file is already gone, so there is nothing left to crash.
    trilio-dms-cli hits the exact same server-side RPC handler a real
    job's mount request would (same RabbitMQ path, same
    is_stale_mount()/cleanup_stale_mount() code), so this exercises the
    identical recovery logic deterministically instead of racing a real
    job's timing.

    Verified live against the real trilio_dms source before writing this
    test (utils.py/server.py/s3vaultfuse_manager.py): every S3 mount
    request proactively calls is_stale_mount() before doing anything
    else, and if stale, calls kill_s3vaultfuse(target_id) then
    cleanup_stale_mount() (which tries fusermount -u -> fusermount -uz ->
    umount -> umount -f -> umount -l, stopping at the first success)
    before proceeding to mount fresh. This test checks the *outcome* of
    that flow (detected -> cleaned up -> new process spawned -> mount
    succeeds) rather than asserting one exact literal command sequence,
    since the real escalation list can legitimately stop at any of its
    5 steps depending on the process's exact state.
    """
    credentials = ['primary']

    @decorators.attr(type='workloadmgr_api')
    def test_dms_s3_fuse_crash_recovery(self):
        reporting.add_test_script(
            str(__name__) + "_s3_fuse_crash_recovery_api")
        try:
            s3_targets = [b for b in self.listBackupTargets()
                         if b['type'] == 's3']
            if not s3_targets:
                raise Exception(
                    "No S3 backup target configured on this environment")
            target = s3_targets[0]
            target_id = target['id']
            mount_path = target['filesystem_export_mount_path']
            LOG.debug(f"S3 target under test: {target_id} ({mount_path})")

            token = self.get_os_token(admin=True)
            node_host = self.get_enabled_compute_node()
            LOG.debug(f"Using node: {node_host}")

            job_id_1 = tvaultconf.dms_mount_job_id
            self.increment_dms_mount_job_id()
            job_id_2 = tvaultconf.dms_mount_job_id
            self.increment_dms_mount_job_id()

            # Establish a real mount + real s3vaultfuse process under
            # our own control.
            out1 = self.run_dms_cli(
                node_host, "mount", job_id_1, target_id, 's3', mount_path,
                filesystem_export=target['filesystem_export'],
                secret_ref=target['secret_ref'], token=token)
            if "new physical mount" in out1:
                reporting.add_test_step(
                    "Verify initial mount establishes a new FUSE process",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify initial mount establishes a new FUSE process",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            pid_before = self.get_dms_s3_pid(node_host, target_id)
            if not pid_before:
                raise Exception(
                    f"No PID file found for target {target_id} on "
                    f"{node_host} right after mounting - can't proceed "
                    f"with the crash simulation")
            LOG.debug(f"s3vaultfuse PID before crash: {pid_before}")

            self.kill_process_on_dms_node(node_host, pid_before)
            LOG.debug(f"Killed s3vaultfuse PID {pid_before} on {node_host}")

            errno_after_kill = self.get_dms_mount_errno(
                node_host, mount_path)
            if errno_after_kill == 107:
                reporting.add_test_step(
                    "Verify mount path is stale (ENOTCONN) after killing "
                    "the FUSE process", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify mount path is stale (ENOTCONN) after killing "
                    f"the FUSE process (got errno={errno_after_kill})",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # Marker before the recovery-triggering mount call, so the
            # log check below only looks at what this attempt produced.
            log_marker = self.get_dms_server_log_marker(node_host)

            # A second, independent mount request (different job_id,
            # representing a new job) must transparently self-heal
            # rather than fail or hang against the stale mount.
            out2 = self.run_dms_cli(
                node_host, "mount", job_id_2, target_id, 's3', mount_path,
                filesystem_export=target['filesystem_export'],
                secret_ref=target['secret_ref'], token=token)
            if "new physical mount" in out2:
                reporting.add_test_step(
                    "Verify a new mount request self-heals and succeeds "
                    "despite the dead FUSE process", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify a new mount request self-heals and succeeds "
                    f"despite the dead FUSE process (output: {out2})",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            new_log = self.get_dms_server_log_since(node_host, log_marker)
            detected = (f"target {target_id}" in new_log
                       and "Stale FUSE mount detected" in new_log)
            cleaned = "Stale mount cleaned up" in new_log
            if detected and cleaned:
                reporting.add_test_step(
                    "Verify DMS server logs show stale-mount detection "
                    "and successful cleanup for this target",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify DMS server logs show stale-mount detection "
                    "and successful cleanup for this target "
                    f"(detected={detected}, cleaned={cleaned})",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            pid_after = self.get_dms_s3_pid(node_host, target_id)
            if pid_after and pid_after != pid_before:
                reporting.add_test_step(
                    "Verify a new s3vaultfuse process (new PID) was "
                    "spawned for this target", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify a new s3vaultfuse process (new PID) was "
                    f"spawned for this target (before={pid_before}, "
                    f"after={pid_after})", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # Cleanup: two independent mount calls (job_id_1, job_id_2)
            # each hold their own ledger reference (confirmed by
            # TC-DMS-04) - release both so the physical mount actually
            # comes down instead of leaking.
            self.run_dms_cli(
                node_host, "unmount", job_id_1, target_id, 's3', mount_path,
                filesystem_export=target['filesystem_export'])
            self.run_dms_cli(
                node_host, "unmount", job_id_2, target_id, 's3', mount_path,
                filesystem_export=target['filesystem_export'])
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()
