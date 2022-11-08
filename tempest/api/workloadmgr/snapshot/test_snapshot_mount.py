import os
import sys

from oslo_log import log as logging

from tempest import config
from tempest import reporting
from tempest import test
from tempest import tvaultconf
from tempest import command_argument_string
from tempest.util import cli_parser
from tempest.util import query_data
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

    @decorators.attr(type='workloadmgr_cli')
    def test_7_snapshot_mount_unmount_full_imagebooted_fvm_cli(self):
        try:
            test_var = "tempest.api.workloadmgr.snapshot.test_image_booted_fvm_"
            tests = [[test_var + "snapshot_mount_invalid_cli", 0],
                     [test_var + "snapshot_mount_valid_cli", 0],
                     [test_var + "snapshot_mounted_list_valid_values_cli", 0],
                     [test_var + "snapshot_mounted_list_invalid_workload_id_cli", 0],
                     [test_var + "snapshot_dismount_cli", 0],
                     [test_var + "snapshot_mounted_list_unmounted_snapshot_cli", 0]]
            reporting.add_test_script(tests[0][0])
            self.kp = self.create_key_pair(tvaultconf.key_pair_name)
            self.vm_id = self.create_vm(key_pair=self.kp)
            self.disk_names = ["vda"]
            fip = self.get_floating_ips()
            LOG.debug("\nAvailable floating ips are {}: \n".format(fip))
            if len(fip) < 2:
                raise Exception("Floating ips unavailable")
            self.set_floating_ip(fip[0], self.vm_id)

            self.frm_id = self.create_vm(
                vm_name="file_recovery_manager",
                flavor_id=CONF.compute.flavor_ref_alt,
                user_data=tvaultconf.user_frm_data,
                key_pair=self.kp,
                image_id=list(CONF.compute.fvm_image_ref.values())[0])
            self.frm_image = list(CONF.compute.fvm_image_ref.keys())[0]
            self.frm_ssh_user = ""
            if "centos" in self.frm_image:
                self.frm_ssh_user = "centos"
            elif "ubuntu" in self.frm_image:
                self.frm_ssh_user = "ubuntu"
            LOG.debug("FRM Instance ID: " + str(self.frm_id))
            LOG.debug("FRM Instance uername: " + str(self.frm_ssh_user))
            self.set_floating_ip(fip[1], self.frm_id)

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.install_qemu(ssh)
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 3)
            md5sums_before_full = self.calculatemmd5checksum(ssh, "/opt")
            LOG.debug(f"md5sums_before_full: {md5sums_before_full}")
            ssh.close()

            # Create workload with API
            try:
                self.wid = self.workload_create([self.vm_id])
                LOG.debug("Workload ID: " + str(self.wid))
            except Exception as e:
                LOG.error(f"Exception: {e}")
                raise Exception("Create workload " \
                                "with image booted vm")
            if (self.wid is not None):
                self.wait_for_workload_tobe_available(self.wid)
                self.workload_status = self.getWorkloadStatus(self.wid)
                if (self.workload_status == "available"):
                    reporting.add_test_step("Create workload " \
                                            "with image booted vm", tvaultconf.PASS)
                else:
                    raise Exception("Create workload " \
                                    "with image booted vm")
            else:
                raise Exception("Create workload with image " \
                                "booted vm")

            full_snapshot_sizes = []
            incr_snapshot_sizes = []
            self.snapshot_id = self.workload_snapshot(self.wid, True)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                                                          self.snapshot_id)
            if (self.snapshot_status == "available"):
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
                self.mount_path = self.get_mountpoint_path()
                self.snapshot_found = self.check_snapshot_exist_on_backend(self.mount_path,
                                                                           self.wid, self.snapshot_id)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on " \
                                            "target backend", tvaultconf.PASS)
                    for disk_name in self.disk_names:
                        full_snapshot_size = self.check_snapshot_size_on_backend(self.mount_path, self.wid,
                                                                                 self.snapshot_id, self.vm_id, disk_name)
                        LOG.debug(f"full snapshot_size for {disk_name}: {full_snapshot_size}")
                        full_snapshot_sizes.append({disk_name: full_snapshot_size})
                    LOG.debug(f"Full snapshot sizes for all disks: {full_snapshot_sizes}")
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create full snapshot")

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 5)
            md5sums_before_incr = self.calculatemmd5checksum(ssh, "/opt")
            LOG.debug(f"md5sums_before_incr: {md5sums_before_incr}")
            ssh.close()

            self.snapshot_id2 = self.workload_snapshot(self.wid, False)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                                                          self.snapshot_id2)
            if (self.snapshot_status == "available"):
                reporting.add_test_step("Create incremental snapshot", tvaultconf.PASS)
                self.mount_path = self.get_mountpoint_path()
                self.snapshot_found = self.check_snapshot_exist_on_backend(self.mount_path,
                                                                           self.wid, self.snapshot_id2)
                LOG.debug(f"snapshot_found: {self.snapshot_found}")
                if self.snapshot_found:
                    reporting.add_test_step("Verify snapshot existence on " \
                                            "target backend", tvaultconf.PASS)
                    for disk_name in self.disk_names:
                        incr_snapshot_size = self.check_snapshot_size_on_backend(self.mount_path, self.wid,
                                                                             self.snapshot_id, self.vm_id, disk_name)
                        LOG.debug(f"incr snapshot_size for {disk_name}: {incr_snapshot_size}")
                        incr_snapshot_sizes.append({disk_name: incr_snapshot_size})
                    LOG.debug(f"Incr snapshot sizes for all disks: {incr_snapshot_sizes}")
                    for dict1, dict2 in zip(full_snapshot_sizes, incr_snapshot_sizes):
                        for key, value in dict1.items():
                            if value > dict2[key]:
                                #print(key, value, dict2[key])
                                reporting.add_test_step(f"Full snapshot size is greater than incr snapshot size for {key}", tvaultconf.PASS)
                            else:
                                reporting.add_test_step(f"Full snapshot size is greater than incr snapshot size for {key}", tvaultconf.FAIL)
                else:
                    raise Exception("Verify snapshot existence on target backend")
            else:
                raise Exception("Create incremental snapshot")

            # Snapshot mount CLI with invalid options
            snapshot_mount_invalid = command_argument_string.snapshot_mount + \
                                     str(self.snapshot_id) + " invalid"
            error = cli_parser.cli_error(snapshot_mount_invalid)
            if error and (str(error.strip('\n')).find('ERROR') != -1):
                LOG.debug("Snapshot mount cli with invalid option returned correct error " + str(error))
                reporting.add_test_step("Snapshot mount cli with invalid option returned correct error",
                                        tvaultconf.PASS)
                tests[0][1] = 1
                reporting.test_case_to_write()
            else:
                LOG.debug("Snapshot mount cli with invalid option returned no error")
                reporting.add_test_step("Snapshot mount cli with invalid option returned correct error",
                                        tvaultconf.FAIL)

            reporting.add_test_script(tests[1][0])
            # Mount full snapshot
            snapshot_mount = command_argument_string.snapshot_mount + \
                             str(self.snapshot_id) + " " + str(self.frm_id)
            mount_status = cli_parser.cli_output(snapshot_mount)
            LOG.debug(f"mount_status for full snapshot: {mount_status}")

            snapshot_mounted = self.wait_for_snapshot_tobe_mounted(
                self.wid, self.snapshot_id, timeout=1800)

            # Show snapshot details using CLI command
            rc = cli_parser.cli_returncode(
                command_argument_string.snapshot_show + self.snapshot_id)
            if rc != 0:
                reporting.add_test_step("Execute snapshot-show command", tvaultconf.FAIL)
                LOG.debug("Command not executed correctly : " + str(rc))
            else:
                reporting.add_test_step("Execute snapshot-show command", tvaultconf.PASS)
                LOG.debug("Command executed correctly : " + str(rc))

            output = cli_parser.cli_output(
                command_argument_string.snapshot_show + self.snapshot_id)
            LOG.debug("Snapshot-show command output : " + str(output))

            if snapshot_mounted and (str(output.strip('\n')).find('mounted') != -1):
                reporting.add_test_step(
                    "Snapshot mount of full snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                    fip[1], self.frm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh).decode('UTF-8').split('\n')
                ssh.close()
                flag = 0
                for i in output_list:
                    if 'vda1.mnt' in i:
                        reporting.add_test_step(
                            "Verify that mountpoint mounted is shown on FVM instance",
                            tvaultconf.PASS)
                        flag = 1
                        if 'File_1' in i:
                            reporting.add_test_step(
                                "Verification of file's existance on mounted snapshot",
                                tvaultconf.PASS)
                        else:
                            reporting.add_test_step(
                                "Verification of file's existance on mounted snapshot",
                                tvaultconf.FAIL)
                    else:
                        pass

                if flag == 0:
                    reporting.add_test_step(
                        "Verify that mountpoint mounted is shown on FVM instance",
                        tvaultconf.FAIL)
                else:
                    pass
            else:
                reporting.add_test_step("Snapshot mount of full snapshot", tvaultconf.FAIL)
                raise Exception("Snapshot mount of full snapshot failed")
            tests[1][1] = 1
            reporting.test_case_to_write()

            reporting.add_test_script(tests[2][0])
            # Mount snapshot mounted list
            snapshot_mounted_list_mount_table = command_argument_string.snapshot_mounted_list + "-f table --workloadid " + \
                                                str(self.wid)
            snapshot_mounted_list_mount_table = cli_parser.cli_output(snapshot_mounted_list_mount_table)
            snapshot_mounted_list_mount_table = snapshot_mounted_list_mount_table.strip()
            LOG.debug(f"snapshot_mounted_list for mounted full snapshot: {snapshot_mounted_list_mount_table}")
            table_format = '| ' + self.snapshot_id + ' |'

            if table_format in snapshot_mounted_list_mount_table:
                reporting.add_test_step(
                    "snapshot_mounted_list for mounted full snapshot in table format", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "snapshot_mounted_list for mounted full snapshot in table format", tvaultconf.FAIL)

            snapshot_mounted_list_mount_csv = command_argument_string.snapshot_mounted_list + "-f csv --workloadid " + \
                                              str(self.wid)
            snapshot_mounted_list_mount_csv = cli_parser.cli_output(snapshot_mounted_list_mount_csv)
            LOG.debug(f"snapshot_mounted_list for mounted full snapshot: {snapshot_mounted_list_mount_csv}")
            csv_format = '"snapshot_id","snapshot_name","workload_id","mounturl","status"'

            if csv_format in snapshot_mounted_list_mount_csv.strip() and self.snapshot_id in snapshot_mounted_list_mount_csv:
                reporting.add_test_step(
                    "snapshot_mounted_list for mounted full snapshot in csv format", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "snapshot_mounted_list for mounted full snapshot in csv format", tvaultconf.FAIL)

            snapshot_mounted_list_mount_json = command_argument_string.snapshot_mounted_list + "-f json --workloadid " + \
                                               str(self.wid)
            snapshot_mounted_list_mount_json = cli_parser.cli_output(snapshot_mounted_list_mount_json)
            snapshot_mounted_list_mount_json = snapshot_mounted_list_mount_json.replace("\n", "").strip()
            LOG.debug(f"snapshot_mounted_list for mounted full snapshot: {snapshot_mounted_list_mount_json}")
            json_format = '[  {    "snapshot_id": "' + self.snapshot_id + '",'

            if json_format in snapshot_mounted_list_mount_json:
                reporting.add_test_step(
                    "snapshot_mounted_list for mounted full snapshot in json format", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "snapshot_mounted_list for mounted full snapshot in json format", tvaultconf.FAIL)

            snapshot_mounted_list_mount_yaml = command_argument_string.snapshot_mounted_list + "-f yaml --workloadid " + \
                                               str(self.wid)
            snapshot_mounted_list_mount_yaml = cli_parser.cli_output(snapshot_mounted_list_mount_yaml)
            snapshot_mounted_list_mount_yaml = snapshot_mounted_list_mount_yaml.replace("\n", "").strip()
            LOG.debug(f"snapshot_mounted_list for mounted full snapshot: {snapshot_mounted_list_mount_yaml}")
            yaml_format = 'snapshot_id: ' + self.snapshot_id

            if yaml_format in snapshot_mounted_list_mount_yaml:
                reporting.add_test_step(
                    "snapshot_mounted_list for mounted full snapshot in yaml format", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "snapshot_mounted_list for mounted full snapshot in yaml format", tvaultconf.FAIL)

            tests[2][1] = 1
            reporting.test_case_to_write()

            reporting.add_test_script(tests[3][0])
            # snapshot mounted list invalid workload id
            snapshot_mounted_list_invalid_wid = command_argument_string.snapshot_mounted_list + "-f json --workloadid " + \
                                                "invalid"
            snapshot_mounted_list_error = cli_parser.cli_error(snapshot_mounted_list_invalid_wid)
            if snapshot_mounted_list_error and (str(snapshot_mounted_list_error.strip('\n')).find('ERROR') != -1):
                LOG.debug("Snapshot mounted list cli with invalid workload id returned correct error " + str(error))
                reporting.add_test_step("Snapshot mounted list cli with invalid workload id returned correct error",
                                        tvaultconf.PASS)
            else:
                LOG.debug("Snapshot mounted list cli with invalid workload id returned no error")
                reporting.add_test_step("Snapshot mounted list cli with invalid workload id returned correct error",
                                        tvaultconf.FAIL)

            tests[3][1] = 1
            reporting.test_case_to_write()

            reporting.add_test_script(tests[4][0])
            # Unmount snapshot
            snapshot_unmount = command_argument_string.snapshot_dismount + \
                               str(self.snapshot_id)
            unmount_status = cli_parser.cli_output(snapshot_unmount)
            LOG.debug(f"unmount_status for full snapshot: {unmount_status}")

            snapshot_unmounted = self.wait_for_snapshot_tobe_available(
                self.wid, self.snapshot_id, timeout=1800)
            if snapshot_unmounted == 'available':
                reporting.add_test_step(
                    "Snapshot unmount of full snapshot", tvaultconf.PASS)
                ssh = self.SshRemoteMachineConnectionWithRSAKey(
                    fip[1], self.frm_ssh_user)
                output_list = self.validate_snapshot_mount(ssh)
                ssh.close()

                if output_list == b'':
                    reporting.add_test_step(
                        "Unmount full snapshot", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Snapshot unmount of full snapshot", tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Snapshot unmount of full snapshot", tvaultconf.FAIL)
            tests[4][1] = 1
            reporting.test_case_to_write()

            reporting.add_test_script(tests[5][0])
            # Unmount snapshot mounted list
            snapshot_mounted_list_unmount = command_argument_string.snapshot_mounted_list + "-f table --workloadid " + \
                                            str(self.wid)
            snapshot_mounted_list_unmount = cli_parser.cli_output(snapshot_mounted_list_unmount)
            LOG.debug(f"snapshot_mounted_list for unmounted full snapshot: {snapshot_mounted_list_unmount}")

            if snapshot_mounted_list_unmount.strip() == '':
                reporting.add_test_step(
                    "snapshot_mounted_list for unmounted full snapshot", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "snapshot_mounted_list for unmounted full snapshot", tvaultconf.FAIL)
            tests[5][1] = 1
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)

        finally:
            for test in tests:
                if test[1] != 1:
                    reporting.set_test_script_status(tvaultconf.FAIL)
                    reporting.add_test_script(test[0])
                    reporting.test_case_to_write()
