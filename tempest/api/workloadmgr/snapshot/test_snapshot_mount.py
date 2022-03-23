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
    fvm_ids = []
    floating_ips_list = []
    wid = ""
    security_group_id = ""
    volumes_ids = []

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()

    def snapshot_mount_full(self, index, fvm_image, wid, full_snapshot_id, fvm_ids, floating_ips_list):
        LOG.debug("mount snapshot of a full snapshot")
        is_mounted = self.mount_snapshot(
            wid, full_snapshot_id, fvm_ids[index], mount_cleanup=False)
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
            # raise Exception(
            #     "Snapshot mount with full_snapshot  does not execute correctly")

        is_verify_mounted, flag = self.verify_snapshot_mount(
            str(floating_ips_list[index]), fvm_image)
        LOG.debug("VALUE OF is_verify_mounted: " + str(is_verify_mounted) + " and flag: " + str(flag))
        if flag == 1:
            reporting.add_test_step(
                "Verify that mountpoint mounted is shown on FVM instance",
                tvaultconf.PASS)
            if is_verify_mounted:
                reporting.add_test_step(
                    "Verification of file's existence on mounted snapshot", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verification of file's existence on mounted snapshot", tvaultconf.FAIL)
        else:
            reporting.add_test_step(
                "Verify that  mountpoint mounted is shown on FVM instance",
                tvaultconf.FAIL)
            reporting.add_test_step(
                "Verification of file's existence on mounted snapshot",
                tvaultconf.FAIL)
            # raise Exception("mountpoint is not showing on FVM instance")
        reporting.test_case_to_write()

    def snapshot_unmount_full(self, index, fvm_image, wid, unmount_snapshot_id, floating_ips_list):
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
            # raise Exception(
            #     "Snapshot unmount with full_snapshot does not execute correctly")

        is_verify_unmounted = self.verify_snapshot_unmount(
            str(floating_ips_list[index]), fvm_image)
        LOG.debug("VALUE OF is_verify_unmounted: " + str(is_verify_unmounted))

        if is_verify_unmounted:
            reporting.add_test_step(
                "Unmounting of a full snapshot", tvaultconf.PASS)
        else:
            reporting.add_test_step(
                "Unmounting of a full snapshot", tvaultconf.FAIL)
            # raise Exception("Unmounting of a snapshot failed")
        reporting.test_case_to_write()

    def snapshot_mount_unmount_incremental(self, index, fvm_image, wid, incremental_snapshot_id, fvm_ids,
                                           floating_ips_list):
        LOG.debug("mount incremental snapshot")
        is_mounted = self.mount_snapshot(
            wid, incremental_snapshot_id, fvm_ids[index], mount_cleanup=False)
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
            # raise Exception(
            #     "Snapshot mount with incremental_snapshot  does not execute correctly")

        is_verify_mounted, flag = self.verify_snapshot_mount(
            str(floating_ips_list[index]), fvm_image)
        LOG.debug("VALUE OF is_verify_mounted: " + str(is_verify_mounted) + " and flag: " + str(flag))
        if flag == 1:
            reporting.add_test_step(
                "Verify that mountpoint mounted is shown on FVM instance",
                tvaultconf.PASS)
            if is_verify_mounted:
                reporting.add_test_step(
                    "Verification of file's existence on mounted snapshot", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verification of file's existence on mounted snapshot", tvaultconf.FAIL)
        else:
            reporting.add_test_step(
                "Verify that  mountpoint mounted is shown on FVM instance",
                tvaultconf.FAIL)
            reporting.add_test_step(
                "Verification of file's existence on mounted snapshot",
                tvaultconf.FAIL)
            # raise Exception("mountpoint is not showing on FVM instance")

        # Unmount incremental snapshot
        LOG.debug("unmount snapshot")
        self.unmount_snapshot(wid, incremental_snapshot_id)

        reporting.test_case_to_write()

    def cleanup_snapshot_mount(self, wid, snapshot_ids, instances_ids, fvm_ids, volumes_ids, security_group_id):
        # Cleanup
        # Delete all snapshots
        for snapshot_id in snapshot_ids:
            self.snapshot_delete(wid, snapshot_id)

        # Delete workload
        self.workload_delete(wid)

        # Delete VMs
        for instance_id in instances_ids:
            self.delete_vm(instance_id)

        for fvm_id in fvm_ids:
            self.delete_vm(fvm_id)

        # Delete volumes
        for volume_id in volumes_ids:
            self.delete_volume(volume_id)

        # Delete security group
        self.delete_security_group(security_group_id)

        # Delete key pair
        self.delete_key_pair(tvaultconf.key_pair_name)

    @test.pre_req({'type': 'snapshot_mount'})
    @decorators.attr(type='workloadmgr_api')
    def test_1_snapshot_mount_unmount_full_imagebooted_fvm(self):
        index = 0
        for fvm_image in list(CONF.compute.fvm_image_ref.keys()):
            reporting.add_test_script(str(__name__) + "_full_snapshot_imagebooted_" + fvm_image)
            # reporting.add_test_script(str(__name__) + "_full_snapshot_imagebooted_fvm_" + fvm_image + "_imagebooted_instance")
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
                global fvm_ids
                global floating_ips_list
                snapshot_ids = self.snapshot_ids
                fvm_ids = self.fvm_ids
                wid = self.wid
                instances_ids = self.instances_ids
                security_group_id = self.security_group_id
                volumes_ids = self.volumes_ids
                floating_ips_list = self.floating_ips_list
                full_snapshot_id = snapshot_ids[0]
                LOG.debug("full snapshot= " + str(full_snapshot_id))
                LOG.debug("floating_ips_list= " + str(floating_ips_list))
                LOG.debug("fvm_ids= " + str(fvm_ids))
                LOG.debug("wid= " + str(wid))
                LOG.debug("instances_ids= " + str(instances_ids))
                LOG.debug("security_group_id= " + str(security_group_id))
                LOG.debug("volumes_ids= " + str(volumes_ids))
                LOG.debug("snapshot_ids= " + str(snapshot_ids))
                # reporting.add_test_script(
                #     str(__name__) + "_full_snapshot_imagebooted_fvm_" + fvm_image + "_volumebooted_instance")
                self.snapshot_mount_full(index, fvm_image, wid, full_snapshot_id, fvm_ids, floating_ips_list)
                # unmount snapshot
                reporting.add_test_script(str(__name__) + "_umount_snapshot_imagebooted_" + fvm_image)
                self.snapshot_unmount_full(index, fvm_image, wid, full_snapshot_id, floating_ips_list)
            except Exception as e:
                LOG.error("Exception: " + str(e))
                reporting.set_test_script_status(tvaultconf.FAIL)
                reporting.test_case_to_write()
            index = index + 1

    @decorators.attr(type='workloadmgr_api')
    def test_2_snapshot_mount_unmount_incremental_imagebooted_fvm(self):
        index = 0
        for fvm_image in list(CONF.compute.fvm_image_ref.keys()):
            reporting.add_test_script(str(__name__) + "_incremental_snapshot_imagebooted_" + fvm_image)
            try:
                LOG.debug("floating_ips_list= " + str(floating_ips_list))
                LOG.debug("fvm_ids= " + str(fvm_ids))
                LOG.debug("wid= " + str(wid))
                LOG.debug("instances_ids= " + str(instances_ids))
                LOG.debug("security_group_id= " + str(security_group_id))
                LOG.debug("volumes_ids= " + str(volumes_ids))
                LOG.debug("snapshot_ids= " + str(snapshot_ids))
                incremental_snapshot_id = snapshot_ids[1]
                self.snapshot_mount_unmount_incremental(index, fvm_image, wid, incremental_snapshot_id, fvm_ids,
                                                        floating_ips_list)
            except Exception as e:
                LOG.error("Exception: " + str(e))
                reporting.set_test_script_status(tvaultconf.FAIL)
                reporting.test_case_to_write()
            index = index + 1

    @decorators.attr(type='workloadmgr_api')
    def test_3_cleanup_snapshot_mount_imagebooted_fvm(self):
        reporting.add_test_script(str(__name__) + "_cleanup_snapshot_imagebooted")
        try:
            LOG.debug("fvm_ids= " + str(fvm_ids))
            LOG.debug("wid= " + str(wid))
            LOG.debug("instances_ids= " + str(instances_ids))
            LOG.debug("security_group_id= " + str(security_group_id))
            LOG.debug("volumes_ids= " + str(volumes_ids))
            LOG.debug("snapshot_ids= " + str(snapshot_ids))
            self.cleanup_snapshot_mount(wid, snapshot_ids, instances_ids, fvm_ids, volumes_ids, security_group_id)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @test.pre_req({'type': 'snapshot_mount_bootfromvol'})
    @decorators.attr(type='workloadmgr_api')
    def test_4_snapshot_mount_unmount_full_volumebooted_fvm(self):
        index = 0
        for fvm_image in list(CONF.compute.fvm_image_ref.keys()):
            reporting.add_test_script(str(__name__) + "_full_snapshot_volumebooted_" + fvm_image)
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
                global fvm_ids
                global floating_ips_list
                snapshot_ids = self.snapshot_ids
                fvm_ids = self.fvm_ids
                wid = self.wid
                instances_ids = self.instances_ids
                security_group_id = self.security_group_id
                volumes_ids = self.volumes_ids
                floating_ips_list = self.floating_ips_list
                full_snapshot_id = snapshot_ids[0]
                LOG.debug("full snapshot= " + str(full_snapshot_id))
                LOG.debug("floating_ips_list= " + str(floating_ips_list))
                LOG.debug("fvm_ids= " + str(fvm_ids))
                LOG.debug("wid= " + str(wid))
                LOG.debug("instances_ids= " + str(instances_ids))
                LOG.debug("security_group_id= " + str(security_group_id))
                LOG.debug("volumes_ids= " + str(volumes_ids))
                LOG.debug("snapshot_ids= " + str(snapshot_ids))
                self.snapshot_mount_full(index, fvm_image, wid, full_snapshot_id, fvm_ids, floating_ips_list)
                # unmount snapshot
                reporting.add_test_script(str(__name__) + "_umount_snapshot_" + fvm_image)
                self.snapshot_unmount_full(index, fvm_image, wid, full_snapshot_id, floating_ips_list)
            except Exception as e:
                LOG.error("Exception: " + str(e))
                reporting.set_test_script_status(tvaultconf.FAIL)
                reporting.test_case_to_write()
            index = index + 1

    @decorators.attr(type='workloadmgr_api')
    def test_5_snapshot_mount_unmount_incremental_volumebooted_fvm(self):
        index = 0
        for fvm_image in list(CONF.compute.fvm_image_ref.keys()):
            reporting.add_test_script(str(__name__) + "_incremental_snapshot_volumebooted_" + fvm_image)
            try:
                incremental_snapshot_id = snapshot_ids[1]
                self.snapshot_mount_unmount_incremental(index, fvm_image, wid, incremental_snapshot_id, fvm_ids,
                                                        floating_ips_list)
            except Exception as e:
                LOG.error("Exception: " + str(e))
                reporting.set_test_script_status(tvaultconf.FAIL)
                reporting.test_case_to_write()
            index = index + 1

    @decorators.attr(type='workloadmgr_api')
    def test_6_cleanup_snapshot_mount_volumebooted_fvm(self):
        reporting.add_test_script(str(__name__) + "_cleanup_snapshot_volumebooted")
        try:
            self.cleanup_snapshot_mount(wid, snapshot_ids, instances_ids, fvm_ids, volumes_ids, security_group_id)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()