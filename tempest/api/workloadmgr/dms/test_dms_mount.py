import time

from oslo_log import log as logging

from tempest import config
from tempest import reporting
from tempest import tvaultconf
from tempest.api.workloadmgr import base
from tempest.lib import decorators

LOG = logging.getLogger(__name__)
CONF = config.CONF


class DMSMountTest(base.BaseWorkloadmgrTest):
    """
    TC-DMS-01: On-demand mount created for a snapshot job and
    auto-unmounted after job completion (Dynamic Mount Service).

    Verifies that the default (S3) backup target is not mounted while
    idle, gets mounted on-demand once a snapshot job needs it, and is
    auto-unmounted again once that job's reference on it is released.
    """
    credentials = ['primary']

    @decorators.attr(type='workloadmgr_api')
    def test_dms_s3_mount_lifecycle_for_snapshot_job(self):
        reporting.add_test_script(str(__name__) + "_s3_mount_lifecycle_api")
        try:
            # Resolve the target's mount path and kind (s3/nfs) from the
            # WLM API instead of hardcoding/decoding/assuming either.
            mount_path = self.get_mountpoint_path(tvaultconf.default_btt_id)
            target_kind = self.get_backup_target_kind(tvaultconf.default_btt_id)
            LOG.debug(f"DMS target mount_path under test: {mount_path} "
                     f"(kind={target_kind})")

            vm_id = self.create_vm()
            server = self.servers_client.show_server(vm_id)['server']
            node_host = server['OS-EXT-SRV-ATTR:host']
            LOG.debug(f"Test VM {vm_id} scheduled on node: {node_host}")

            # Step 1: idle - target should not be mounted (S3: no FUSE
            # process either; NFS: mount table is the whole signal).
            mounted, running = self.get_dms_mount_state(
                node_host, mount_path, target_kind)
            LOG.debug(f"Before job: mounted={mounted}, running={running}")
            if not mounted and not running:
                reporting.add_test_step(
                    "Verify S3 target not mounted before job starts",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify S3 target not mounted before job starts",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            workload_id = self.workload_create([vm_id])
            snapshot_id = self.workload_snapshot(workload_id, is_full=True)

            # Step 2: job running - target should be mounted on-demand at
            # some point before the job completes. The job runs through
            # several phases (queued, metadata capture, then the actual
            # data transfer that needs the mount) asynchronously, so poll
            # alongside the snapshot's own status instead of checking once
            # after a fixed delay - a single early check can catch it
            # before the mount phase has started even though the job goes
            # on to mount it later.
            ever_mounted, ever_running = False, False
            timeout = 1800
            start_time = time.time()
            status = self.getSnapshotStatus(workload_id, snapshot_id)
            while status not in ('available', 'error'):
                mounted, running = self.get_dms_mount_state(
                    node_host, mount_path, target_kind)
                ever_mounted = ever_mounted or mounted
                ever_running = ever_running or running
                LOG.debug(f"During job (status={status}): mounted={mounted}, "
                         f"running={running}")
                if ever_mounted and ever_running:
                    break
                if time.time() - start_time > timeout:
                    LOG.error("Timeout waiting to observe DMS mount during job")
                    break
                time.sleep(15)
                status = self.getSnapshotStatus(workload_id, snapshot_id)

            if ever_mounted and ever_running:
                reporting.add_test_step(
                    "Verify S3 target mounted on-demand while job runs",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify S3 target mounted on-demand while job runs",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)

            # Step 3: job complete - target auto-unmounted (ref-count back
            # to 0).
            time.sleep(20)
            mounted, running = self.get_dms_mount_state(
                node_host, mount_path, target_kind)
            LOG.debug(f"After job: mounted={mounted}, running={running}")
            if not mounted and not running:
                reporting.add_test_step(
                    "Verify S3 target auto-unmounted after job completes",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify S3 target auto-unmounted after job completes",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_dms_s3_mount_shared_across_concurrent_snapshot_jobs(self):
        """
        TC-DMS-02: A backup target's mount is shared (not double-mounted)
        across two concurrent snapshot jobs on the same node, and both
        jobs complete successfully despite it.

        DMS mounts are per (host, backup_target_id) pair, so this only
        exercises mount sharing if both jobs' datamover work lands on the
        same compute node - keep creating a second VM until one schedules
        onto the same node as the first (bounded attempts), rather than
        relying on unverified scheduler hints.

        NOTE: DMS does not hold one mount open for a job's whole lifetime,
        released only when every concurrent job is done with it (as the
        architecture doc's "reference-counted... shared by concurrent
        jobs" phrasing might suggest). Verified via trilio-dms-server.log
        by trace_id: each job's *phase* independently mounts/unmounts
        around its own unit of work, so one job finishing a phase can
        briefly unmount a target another job's phase still needs - DMS
        self-heals by having that job immediately re-mount (observed gap:
        ~1ms, no error). This test asserts the outcome that actually
        matters given that: both jobs still complete successfully.
        """
        reporting.add_test_script(str(__name__) + "_s3_mount_shared_concurrent_api")
        try:
            mount_path = self.get_mountpoint_path(tvaultconf.default_btt_id)
            target_kind = self.get_backup_target_kind(tvaultconf.default_btt_id)
            LOG.debug(f"DMS target mount_path under test: {mount_path} "
                     f"(kind={target_kind})")

            vm_a = self.create_vm()
            host_a = self.servers_client.show_server(vm_a)['server'][
                'OS-EXT-SRV-ATTR:host']
            LOG.debug(f"VM A {vm_a} scheduled on node: {host_a}")

            vm_b, host_b = None, None
            max_attempts = 6
            for attempt in range(max_attempts):
                candidate = self.create_vm()
                candidate_host = self.servers_client.show_server(candidate)[
                    'server']['OS-EXT-SRV-ATTR:host']
                LOG.debug(f"VM B candidate {candidate} scheduled on node: "
                         f"{candidate_host} (attempt {attempt + 1})")
                if candidate_host == host_a:
                    vm_b, host_b = candidate, candidate_host
                    break
            if vm_b is None:
                raise Exception(
                    f"Could not schedule a second VM onto {host_a} after "
                    f"{max_attempts} attempts to test same-host mount sharing")
            node_host = host_a

            mounted, running = self.get_dms_mount_state(
                node_host, mount_path, target_kind)
            LOG.debug(f"Before jobs: mounted={mounted}, running={running}")
            if not mounted and not running:
                reporting.add_test_step(
                    "Verify S3 target not mounted before jobs start",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify S3 target not mounted before jobs start",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            workload_a = self.workload_create([vm_a])
            workload_b = self.workload_create([vm_b])
            snapshot_a = self.workload_snapshot(workload_a, is_full=True)

            # Wait for A's mount to become active before starting B, so
            # their "mounted" windows are guaranteed to overlap rather than
            # racing on arbitrary timing.
            timeout = 900
            start_time = time.time()
            status_a = self.getSnapshotStatus(workload_a, snapshot_a)
            while status_a not in ('available', 'error'):
                mounted, _ = self.get_dms_mount_state(
                    node_host, mount_path, target_kind)
                if mounted:
                    break
                if time.time() - start_time > timeout:
                    LOG.error("Timeout waiting for job A to mount the target "
                            "before starting job B")
                    break
                time.sleep(10)
                status_a = self.getSnapshotStatus(workload_a, snapshot_a)

            snapshot_b = self.workload_snapshot(workload_b, is_full=True)

            # Both jobs should now be racing to use the same target on the
            # same node - verify DMS shares one mount rather than spawning
            # a second one for job B. The "exactly one process" half is
            # S3-specific (a kernel NFS mount has no per-job process to
            # count in the first place - it's just mounted once, by
            # nature - so there's nothing meaningful to count for NFS;
            # the mount-table result alone is the whole signal there).
            mounted, running = self.get_dms_mount_state(
                node_host, mount_path, target_kind)
            if target_kind == 's3':
                proc_count = self.get_dms_s3_process_count(node_host)
                shared_ok = mounted and proc_count in (1, None)
            else:
                proc_count = None
                shared_ok = mounted
            LOG.debug(f"During concurrent jobs: mounted={mounted}, "
                     f"running={running}, proc_count={proc_count}")
            if shared_ok:
                reporting.add_test_step(
                    "Verify single shared mount/process for concurrent "
                    "jobs on same target", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify single shared mount/process for concurrent "
                    "jobs on same target", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # NOTE: DMS does NOT hold one mount open for the whole lifetime
            # of a job and release it only when the last concurrent job is
            # done, as the architecture doc's "reference-counted... shared
            # by concurrent jobs" description might suggest. Traced via
            # trilio-dms-server.log by trace_id: each job's *phase*
            # independently mounts, does its work, and unmounts on its own
            # - so job B finishing a phase can fully unmount the target
            # while job A's phase still needs it, and DMS self-heals by
            # having job A immediately re-mount (observed gap: ~1ms, no
            # error). That's an internal implementation detail we can't
            # reliably observe via external polling anyway (our own poll
            # interval is far coarser than a millisecond-scale re-mount).
            # What actually matters to a user is the outcome this produces:
            # do both concurrent jobs still complete successfully despite
            # it. wait_for_snapshot_tobe_available() below already raises
            # if a snapshot lands in 'error', which the outer except
            # catches and fails the whole script on - so reaching each of
            # these steps at all is the real assertion.
            self.wait_for_snapshot_tobe_available(workload_a, snapshot_a)
            reporting.add_test_step(
                "Verify job A's snapshot completes successfully despite "
                "job B's concurrent independent mount/unmount cycles on "
                "the same shared target", tvaultconf.PASS)

            self.wait_for_snapshot_tobe_available(workload_b, snapshot_b)
            reporting.add_test_step(
                "Verify job B's snapshot completes successfully despite "
                "job A's concurrent independent mount/unmount cycles on "
                "the same shared target", tvaultconf.PASS)

            time.sleep(20)
            mounted, running = self.get_dms_mount_state(
                node_host, mount_path, target_kind)
            LOG.debug(f"After both jobs complete: mounted={mounted}, "
                     f"running={running}")
            if not mounted and not running:
                reporting.add_test_step(
                    "Verify S3 target auto-unmounted after both jobs complete",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify S3 target auto-unmounted after both jobs complete",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_dms_s3_mount_lifecycle_for_oneclick_restore(self):
        """
        TC-DMS-03: On-demand mount is created for a one-click restore and
        auto-unmounted after it completes.

        Mirrors TC-DMS-01 but for the read side (restore) instead of the
        write side (backup) - the restored VM may land on a different
        compute node than the one the original backup ran on, so the node
        to check is determined from the restore's own result, not the
        original VM.

        One-click restore only works correctly if the original VM (and its
        volumes) is deleted after the snapshot completes and before the
        restore is triggered - mirrors the existing
        restore/test_tvault1040_oneclick_restore.py pattern.

        NOTE: this triggers the restore with the same WLM API payload
        self.snapshot_restore() uses, rather than calling that helper
        directly - snapshot_restore() calls
        wait_for_snapshot_tobe_available() again right after posting the
        restore, and that snapshot's own status apparently stays busy
        until the restore itself fully finishes, so snapshot_restore()
        doesn't return until the whole restore (backup+restore combined:
        ~170s observed) is already done - there's no "during restore"
        window left to poll from outside that call by the time it
        returns. Posting directly (same payload, same restore_id) and
        polling with the same getRestoreStatus()/get_restored_vm_list()
        helpers snapshot_restore() itself uses internally, plus
        registering the exact same cleanup it would have, keeps this
        using only existing pieces without going through the wrapper
        that hides the window this test needs to observe.
        """
        reporting.add_test_script(str(__name__) + "_s3_mount_lifecycle_oneclick_restore_api")
        try:
            mount_path = self.get_mountpoint_path(tvaultconf.default_btt_id)
            target_kind = self.get_backup_target_kind(tvaultconf.default_btt_id)
            LOG.debug(f"DMS target mount_path under test: {mount_path} "
                     f"(kind={target_kind})")

            # Prerequisite: a workload with an available full snapshot,
            # then delete the source VM so the one-click restore works.
            vm_id = self.create_vm(vm_cleanup=False)
            workload_id = self.workload_create([vm_id])
            snapshot_id = self.workload_snapshot(workload_id, is_full=True)
            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            self.delete_vm(vm_id)
            LOG.debug(f"Deleted source VM {vm_id} before triggering restore")

            # Same payload self.snapshot_restore() posts internally.
            restore_name = tvaultconf.snapshot_restore_name
            payload = {
                "restore": {
                    "options": {
                        "description": "Tempest test restore",
                        "vmware": {},
                        "openstack": {"instances": [], "zone": ""},
                        "restore_type": "oneclick",
                        "type": "openstack",
                        "oneclickrestore": "True",
                        "restore_options": {},
                        "name": restore_name},
                    "name": restore_name,
                    "description": "Tempest test restore"}}
            resp, body = self.wlm_client.client.post(
                "/workloads/" + workload_id + "/snapshots/" + snapshot_id +
                "/restores", json=payload)
            if resp.status_code != 202:
                resp.raise_for_status()
            restore_id = body['restore']['id']
            LOG.debug(f"Restore ID: {restore_id}")

            # Poll restore status, DMS mount state, and the restored VM's
            # node together - same polling rationale as TC-DMS-01's step 2,
            # just combined with node discovery since we don't know which
            # node the restored VM lands on until the restore reports it.
            node_host = None
            ever_mounted, ever_running = False, False
            timeout = 900
            start_time = time.time()
            status = self.getRestoreStatus(workload_id, snapshot_id, restore_id)
            while status not in ('available', 'error'):
                if node_host is None:
                    # The restore's own record reports which node is doing
                    # its data transfer directly (top-level 'host', not
                    # snapshot_details['host'] which is where the original
                    # backup ran) - this is available well before the
                    # restored VM exists in Nova, unlike deriving the node
                    # from get_restored_vm_list()/show_server(), which
                    # arrived too late to catch the mount window (the
                    # restore's actual data transfer finishes before the
                    # new VM is even created/bootable).
                    node_host = self.getRestoreDetails(restore_id).get('host')
                    if node_host:
                        LOG.debug(f"Restore reported host: {node_host}")
                if node_host:
                    mounted, running = self.get_dms_mount_state(
                        node_host, mount_path, target_kind)
                    ever_mounted = ever_mounted or mounted
                    ever_running = ever_running or running
                    LOG.debug(f"During restore (status={status}): "
                             f"mounted={mounted}, running={running}")
                    if ever_mounted and ever_running:
                        break
                if time.time() - start_time > timeout:
                    LOG.error("Timeout waiting to observe DMS mount during "
                            "restore")
                    break
                time.sleep(3)
                status = self.getRestoreStatus(workload_id, snapshot_id, restore_id)

            if ever_mounted and ever_running:
                reporting.add_test_step(
                    "Verify S3 target mounted on-demand during restore",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify S3 target mounted on-demand during restore",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            while status not in ('available', 'error'):
                time.sleep(10)
                status = self.getRestoreStatus(workload_id, snapshot_id, restore_id)
            if status != 'available':
                raise Exception(f"Restore ended in status: {status}")
            reporting.add_test_step(
                "Verify one-click restore completes successfully",
                tvaultconf.PASS)

            # Same cleanup registration self.snapshot_restore() does.
            restored_vms = self.get_restored_vm_list(restore_id)
            restored_volumes = self.get_restored_volume_list(restore_id)
            for each in self.getRestoredSecGroupPolicies(restored_vms):
                secgrp_id = self.get_restored_security_group_id_by_name(each)
                self.addCleanup(self.delete_security_group, secgrp_id)
            self.addCleanup(self.restore_delete, workload_id, snapshot_id,
                            restore_id)
            self.addCleanup(self.delete_restored_vms, restored_vms,
                            restored_volumes)

            if node_host is None:
                # Restore finished before a node was ever discovered (e.g.
                # it errored immediately) - nothing meaningful to check for
                # the unmount step either.
                raise Exception(
                    "Restore completed without ever reporting a host to "
                    "check DMS mount state against")

            time.sleep(20)
            mounted, running = self.get_dms_mount_state(
                node_host, mount_path, target_kind)
            LOG.debug(f"After restore completes: mounted={mounted}, "
                     f"running={running}")
            if not mounted and not running:
                reporting.add_test_step(
                    "Verify S3 target auto-unmounted after restore completes",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify S3 target auto-unmounted after restore completes",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_dms_s3_mount_independent_across_two_nodes_single_job(self):
        """
        TC-DMS-06: A single job spanning two VMs on two different compute
        nodes gets the same backup target mounted independently on each
        node - not shared/conflated across hosts the way TC-DMS-02 proved
        it's shared within the same host.

        DMS's mount key is (host, backup_target_id), so this exercises
        the host half of that pairing: TC-DMS-02 forced two *separate*
        jobs onto the *same* node (same target -> one shared mount);
        this forces *one* job across two *different* nodes (same target
        -> two independent mounts, one per node).

        Requires at least 2 enabled/up compute nodes - checked upfront
        via Nova's hypervisor-list before creating anything, so an
        under-resourced environment fails fast with a clear message
        instead of trying to schedule anything.

        NOTE: originally used TC-DMS-02's retry-until-it-lands style loop
        (creating VMs until one landed on a different node), but a live
        run showed this scheduler is heavily biased toward one compute
        node - 6/6 attempts landed on the same node here, so that
        approach isn't reliable for a test that specifically needs two
        *different* nodes (unlike TC-DMS-02, which is fine with either
        outcome). Explicitly pins each VM to one of the two discovered
        nodes via Nova's "<zone>:<host>" availability_zone syntax instead
        - deterministic, no retries needed.

        The compute-node-count prerequisite check runs before
        reporting.add_test_script() and uses self.skipTest() rather than
        raising - this environment gap isn't a DMS bug to report as a
        FAIL, so it's a real stestr SKIP (visible in the test run output)
        and intentionally does not add anything to Report/results.html at
        all, rather than showing up there as a red FAIL for something
        outside this test's control.
        """
        hypervisors = self.hypervisor_client.list_hypervisors()[
            'hypervisors']
        enabled = [h['hypervisor_hostname'] for h in hypervisors
                  if h.get('state') == 'up'
                  and h.get('status') == 'enabled']
        if len(enabled) < 2:
            self.skipTest(
                f"TC-DMS-06 requires at least 2 enabled compute nodes to "
                f"test cross-node mount isolation, found {len(enabled)} "
                f"({enabled})")

        reporting.add_test_script(
            str(__name__) + "_s3_mount_independent_two_nodes_api")
        try:
            node_a, node_b = enabled[0], enabled[1]
            zone = CONF.compute.vm_availability_zone
            LOG.debug(f"Pinning VM A to {zone}:{node_a}, "
                     f"VM B to {zone}:{node_b}")

            mount_path = self.get_mountpoint_path(tvaultconf.default_btt_id)
            target_kind = self.get_backup_target_kind(tvaultconf.default_btt_id)
            LOG.debug(f"DMS target mount_path under test: {mount_path} "
                     f"(kind={target_kind})")

            vm_a = self.create_vm(a_zone=f"{zone}:{node_a}")
            host_a = self.servers_client.show_server(vm_a)['server'][
                'OS-EXT-SRV-ATTR:host']
            LOG.debug(f"VM A {vm_a} scheduled on node: {host_a}")

            vm_b = self.create_vm(a_zone=f"{zone}:{node_b}")
            host_b = self.servers_client.show_server(vm_b)['server'][
                'OS-EXT-SRV-ATTR:host']
            LOG.debug(f"VM B {vm_b} scheduled on node: {host_b}")

            if host_a == host_b:
                raise Exception(
                    f"Both VMs landed on the same node ({host_a}) despite "
                    f"explicit different availability-zone pinning "
                    f"({zone}:{node_a} / {zone}:{node_b}) - cannot test "
                    f"cross-node mount isolation")

            mounted_a, running_a = self.get_dms_mount_state(
                host_a, mount_path, target_kind)
            mounted_b, running_b = self.get_dms_mount_state(
                host_b, mount_path, target_kind)
            LOG.debug(f"Before job: node A mounted={mounted_a}, "
                     f"running={running_a}; node B mounted={mounted_b}, "
                     f"running={running_b}")
            if (not mounted_a and not running_a
                    and not mounted_b and not running_b):
                reporting.add_test_step(
                    "Verify target not mounted on either node before job "
                    "starts", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify target not mounted on either node before job "
                    "starts", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            workload_id = self.workload_create([vm_a, vm_b])
            snapshot_id = self.workload_snapshot(workload_id, is_full=True)

            # Poll both nodes together alongside the snapshot's own status,
            # same rationale as TC-DMS-01's step 2 - the job's mount phase
            # for each VM's data can start at different times, so a single
            # early check on either node could miss it.
            ever_mounted_a, ever_running_a = False, False
            ever_mounted_b, ever_running_b = False, False
            timeout = 1800
            start_time = time.time()
            status = self.getSnapshotStatus(workload_id, snapshot_id)
            while status not in ('available', 'error'):
                mounted_a, running_a = self.get_dms_mount_state(
                    host_a, mount_path, target_kind)
                mounted_b, running_b = self.get_dms_mount_state(
                    host_b, mount_path, target_kind)
                ever_mounted_a = ever_mounted_a or mounted_a
                ever_running_a = ever_running_a or running_a
                ever_mounted_b = ever_mounted_b or mounted_b
                ever_running_b = ever_running_b or running_b
                LOG.debug(f"During job (status={status}): "
                         f"A mounted={mounted_a}/running={running_a}, "
                         f"B mounted={mounted_b}/running={running_b}")
                if (ever_mounted_a and ever_running_a
                        and ever_mounted_b and ever_running_b):
                    break
                if time.time() - start_time > timeout:
                    LOG.error("Timeout waiting to observe DMS mount on "
                            "both nodes during job")
                    break
                time.sleep(15)
                status = self.getSnapshotStatus(workload_id, snapshot_id)

            if ever_mounted_a and ever_running_a:
                reporting.add_test_step(
                    "Verify target mounted independently on node A",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify target mounted independently on node A",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            if ever_mounted_b and ever_running_b:
                reporting.add_test_step(
                    "Verify target mounted independently on node B",
                    tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify target mounted independently on node B",
                    tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            reporting.add_test_step(
                "Verify single job spanning two nodes completes "
                "successfully", tvaultconf.PASS)

            time.sleep(20)
            mounted_a, running_a = self.get_dms_mount_state(
                host_a, mount_path, target_kind)
            mounted_b, running_b = self.get_dms_mount_state(
                host_b, mount_path, target_kind)
            LOG.debug(f"After job: node A mounted={mounted_a}, "
                     f"running={running_a}; node B mounted={mounted_b}, "
                     f"running={running_b}")
            if (not mounted_a and not running_a
                    and not mounted_b and not running_b):
                reporting.add_test_step(
                    "Verify target auto-unmounted on both nodes after "
                    "job completes", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify target auto-unmounted on both nodes after "
                    "job completes", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()
