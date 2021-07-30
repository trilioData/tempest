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
    wid = ""
    security_group_id = ""
    volumes_ids = []

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()

    @test.pre_req({'type': 'snapshot_mount'})
    @decorators.attr(type='smoke')
    @decorators.idempotent_id('90dfa684-171c-40c7-a195-df53671bec4b')
    @decorators.attr(type='workloadmgr_api')
    def test_1_snapshot_mount_full(self):
        reporting.add_test_script(str(__name__) + "_full_snasphot")
        try:
            if self.exception != "":
                LOG.debug("pre req failed")
                reporting.add_test_step(str(self.exception), tvaultconf.FAIL)
                raise Exception(str(self.exception))
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
            is_mounted = self.mount_snapshot(
                wid, full_snapshot_id, fvm_id, mount_cleanup=False)
            LOG.debug("VALUE OF is_mounted: " + str(is_mounted))
            if is_mounted:
                LOG.debug(" mount snapshot with full snapshot is successful")
                reporting.add_test_step(
                    "Verification of mount snapshot with full snapshot",
                    tvaultconf.PASS)
            else:
                LOG.debug("mount snapshot with full snapshot is unsuccessful")
                reporting.add_test_step(
                    "Verification of mount snapshot with full snapshot",
                    tvaultconf.FAIL)
                raise Exception(
                    "Snapshot mount with full_snapshot  does not execute correctly")

            LOG.debug("validate that snapshot is mounted on FVM")
            ssh = self.SshRemoteMachineConnectionWithRSAKey(
                str(floating_ips_list[1]), CONF.validation.fvm_ssh_user)
            output_list = self.validate_snapshot_mount(ssh).decode('UTF-8').split('\n')
            ssh.close()
            flag = 0
            for i in output_list:
                if 'vdbb' in i:
                    LOG.debug(
                        "connect to fvm and check mountpoint is mounted on FVM instance")
                    reporting.add_test_step(
                        "Verify that mountpoint mounted is shown on FVM instance",
                        tvaultconf.PASS)
                    flag = 1
                    if 'File_1' in i:
                        LOG.debug("check that file exists on mounted snapshot")
                        reporting.add_test_step(
                            "Verification of file's existance on moutned snapshot", tvaultconf.PASS)
                    else:
                        LOG.debug("file does not found on FVM instacne")
                        reporting.add_test_step(
                            "Verification of file's existance on moutned snapshot", tvaultconf.FAIL)
                        raise Exception("file does not found on FVM instacne")
                else:
                    pass

            if flag == 0:
                LOG.debug(
                    "mount snapshot with full snapshot is unsuccessful on FVM")
                reporting.add_test_step(
                    "Verify that  mountpoint mounted is shown on FVM instance",
                    tvaultconf.FAIL)
                LOG.debug("file does not found on FVM instacne")
                reporting.add_test_step(
                    "Verification of file's existance on moutned snapshot",
                    tvaultconf.FAIL)
                raise Exception("mountpoint is not showing on FVM instance")
            else:
                pass
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('28fd0710-ef00-42b0-93f0-9dbb3ffc5bee')
    @decorators.attr(type='workloadmgr_api')
    def test_2_umount_snapshot(self):
        reporting.add_test_script(str(__name__) + "_umount_snapshot")
        try:
            global instances_ids
            global snapshot_ids
            global wid
            global security_group_id
            global volumes_ids
            global fvm_id
            global floating_ips_list
            instances_ids = instances_ids
            snapshot_ids = snapshot_ids
            wid = wid
            volumes_ids = volumes_ids
            security_group_id = security_group_id
            fvm_id = fvm_id
            unmount_snapshot_id = snapshot_ids[0]
            floating_ips_list = floating_ips_list

            LOG.debug("unmount snapshot")
            is_unmounted = self.unmount_snapshot(wid, unmount_snapshot_id)
            LOG.debug("VALUE OF is_unmounted: " + str(is_unmounted))
            if is_unmounted:
                LOG.debug("unmount snapshot with full snapshot is  successful")
                reporting.add_test_step(
                    "Verification of unmount snapshot with full snapshot",
                    tvaultconf.PASS)
            else:
                LOG.debug("unmount snapshot with full snapshot is unsuccessful")
                reporting.add_test_step(
                    "Verification of unmount snapshot with full snapshot",
                    tvaultconf.FAIL)
                raise Exception(
                    "Snapshot unmount with full_snapshot does not execute correctly")

            LOG.debug("validate that snapshot is unmounted from FVM")
            ssh = self.SshRemoteMachineConnectionWithRSAKey(
                str(floating_ips_list[1]), CONF.validation.fvm_ssh_user)
            output_list = self.validate_snapshot_mount(ssh)
            ssh.close()

            if output_list == b'':
                LOG.debug("Unmounting successful")
                reporting.add_test_step(
                    "Unmounting of a full snapshot", tvaultconf.PASS)
            else:
                LOG.debug("Unmounting unsuccessful")
                reporting.add_test_step(
                    "Unmounting of a full snapshot", tvaultconf.FAIL)
                raise Exception("Unmouting of a snapshot failed")
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('215e0c36-8911-4167-aaea-8c07d21212f3')
    @decorators.attr(type='workloadmgr_api')
    def test_3_snapshot_mount_incremental(self):
        reporting.add_test_script(str(__name__) + "_incremental_snasphot")
        try:
            global instances_ids
            global snapshot_ids
            global wid
            global security_group_id
            global volumes_ids
            global fvm_id
            global floating_ips_list
            instances_ids = instances_ids
            snapshot_ids = snapshot_ids
            wid = wid
            volumes_ids = volumes_ids
            security_group_id = security_group_id
            fvm_id = fvm_id
            incremental_snapshot_id = snapshot_ids[1]
            floating_ips_list = floating_ips_list

            LOG.debug("mount incremental snapshot")
            is_mounted = self.mount_snapshot(
                wid, incremental_snapshot_id, fvm_id)
            LOG.debug("VALUE OF is_mounted: " + str(is_mounted))
            if is_mounted:
                LOG.debug(
                    " mount snapshot with incremental snapshot is  successful")
                reporting.add_test_step(
                    "Verification of mount snapshot with incremental snapshot",
                    tvaultconf.PASS)
            else:
                LOG.debug(
                    "mount snapshot with incremental snapshot is unsuccessful")
                reporting.add_test_step(
                    "Verification of mount snapshot with incremental snapshot",
                    tvaultconf.FAIL)
                raise Exception(
                    "Snapshot mount with incremental_snapshot  does not execute correctly")

            LOG.debug("validate that snapshot is mounted on FVM")
            ssh = self.SshRemoteMachineConnectionWithRSAKey(
                str(floating_ips_list[1]), CONF.validation.fvm_ssh_user)
            output_list = self.validate_snapshot_mount(ssh).decode('UTF-8').split('\n')
            ssh.close()

            flag = 0
            for i in output_list:
                if 'vdbb' in i:
                    LOG.debug(
                        "connect to fvm and check mountpoint is mounted on FVM instance")
                    reporting.add_test_step(
                        "Verify that mountpoint mounted is shown on FVM instance",
                        tvaultconf.PASS)
                    flag = 1
                    if 'File_1' in i:
                        LOG.debug(
                            "check that file is exist on mounted snapshot")
                        reporting.add_test_step(
                            "Verification of file's existance on mounted snapshot", tvaultconf.PASS)
                    else:
                        LOG.debug("file does not found on FVM instacne")
                        reporting.add_test_step(
                            "Verification of file's existance on mounted snapshot", tvaultconf.FAIL)
                        raise Exception("file does not found on FVM instacne")
                else:
                    pass

            if flag == 0:
                LOG.debug(
                    "mount snapshot with full snapshot is unsuccessful on FVM")
                reporting.add_test_step(
                    "Verify that  mountpoint mounted is shown on FVM instance",
                    tvaultconf.FAIL)
                LOG.debug("file does not found on FVM instacne")
                reporting.add_test_step(
                    "Verification of file's existance on mounted snapshot",
                    tvaultconf.FAIL)
                raise Exception("mountpoint is not showing on FVM instance")
            else:
                pass

            # Cleanup
            # Unmount incremental snapshot
            self.unmount_snapshot(wid, incremental_snapshot_id)

            # Delete all snapshots
            for snapshot_id in snapshot_ids:
                self.snapshot_delete(wid, snapshot_id)

            # Delete workload
            self.workload_delete(wid)

            # Delete VMs
            for instance_id in instances_ids:
                self.delete_vm(instance_id)
            self.delete_vm(fvm_id)

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
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
