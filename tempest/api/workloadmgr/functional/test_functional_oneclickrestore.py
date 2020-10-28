from tempest.util import query_data
from tempest.util import cli_parser
from tempest import command_argument_string
import time
from tempest import reporting
from tempest import tvaultconf
from oslo_log import log as logging
from tempest.lib import decorators
from tempest import config
from tempest.api.workloadmgr import base
import sys
import os
import json
import random
import tempest
import unicodedata
import operator
import collections
sys.path.append(os.getcwd())

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    def create_kps(self, count):
        key_pairs = []
        for each in range(1, count + 1):
            c = "tempest_test_key_pair"
            s = c + str(each)
            kp = self.create_key_pair(s, keypair_cleanup=True)
            key_pairs.append((s, kp))
            LOG.debug("\nKey_pair {0}  : {1}\n".format(s, kp))
        return(key_pairs)

    def create_sec_groups(self, count):
        sec_groups = []
        ip_protocols = ["TCP", "UDP"]
        for each in range(1, count + 1):
            sgid = self.create_security_group(
                name="sample_security_group-{}".format(each),
                description="security group",
                secgrp_cleanup=True)
            sec_groups.append(sgid)
            self.add_security_group_rule(
                parent_grp_id=sgid,
                ip_proto=random.choice(ip_protocols),
                from_prt=2000,
                to_prt=2100)
            self.add_security_group_rule(
                parent_grp_id=sgid,
                ip_proto="TCP",
                from_prt=22,
                to_prt=22)
        return(sec_groups)

    def multiple_vms(self, vm_count, key_pairs, sec_groups):
        vms = {}
        boot_vols = []
        for each in range(1, vm_count + 1):
            if each <= int(vm_count / 2):
                kptouple = random.choice(key_pairs)
                vm_id = self.create_vm(
                    security_group_id=random.choice(sec_groups),
                    key_pair=kptouple[1],
                    key_name=kptouple[0],
                    vm_cleanup=False)
                vms[vm_id] = [kptouple[0]]
            else:
                boot_volume_id = self.create_volume(
                    size=tvaultconf.bootfromvol_vol_size,
                    image_id=CONF.compute.image_ref,
                    volume_cleanup=True)
                boot_vols.append(boot_volume_id)
                self.set_volume_as_bootable(boot_volume_id)
                LOG.debug("Bootable Volume ID : " + str(boot_volume_id))

                block_mapping_details = [{"source_type": "volume",
                                          "delete_on_termination": "false",
                                          "boot_index": 0,
                                          "uuid": boot_volume_id,
                                          "destination_type": "volume"}]

                # Create instance
                kptouple = random.choice(key_pairs)
                vm_id = self.create_vm(
                    security_group_id=random.choice(sec_groups),
                    key_pair=kptouple[1],
                    key_name=kptouple[0],
                    block_mapping_data=block_mapping_details,
                    vm_cleanup=False)
                LOG.debug("VM ID : " + str(vm_id))
                vms[vm_id] = [kptouple[0]]
        return(vms, boot_vols)

    def attach_vols(self, vms):
        nvol = [0, 1, 2, 3]
        for vm in vms:
            volumes = []
            no = random.choice(nvol)
            for every_vol in range(0, no):
                volume_id = self.create_volume(volume_cleanup=True)
                volumes.append(volume_id)
                LOG.debug("Volume ID: " + str(volume_id))
                self.attach_volume(volume_id, vm, attach_cleanup=False)
                LOG.debug("Volume attached")
            vms[vm].append(volumes)
        return(vms)

    def fill_data(self, vms):
        volumes_parts = ["/dev/vdb", "/dev/vdc", "/dev/vdd"]
        mount_points = ["mount_data_a", "mount_data_b", "mount_data_c"]
        fips = []
        mdsums_original = {}
        for each in vms:
            mdsum = ""
            fip = ""
            if len(vms[each][1]) != 0:
                fip = self.assign_floating_ips(each, False)
                fips.append((each, fip))
                vms[each].append(fip)
                for i in range(0, len(vms[each][1])):
                    self.data_ops(fip, vms[each][0],
                                  volumes_parts[i], mount_points[i], 3)
                    mdsum = mdsum + \
                        self.calcmd5sum(fip, vms[each][0], mount_points[i])
                    mdsums_original[each] = mdsum
            else:
                pass
        return(mdsums_original)

    def assign_floating_ips(self, vm_id, fipcleanup):
        fip = self.get_floating_ips()
        self.set_floating_ip(str(fip[0]), vm_id, floatingip_cleanup=fipcleanup)
        return(fip[0])

    def data_ops(
        self,
        flo_ip,
        key_name,
        volumes_part,
        mount_point,
        file_count):
        ssh = self.SshRemoteMachineConnectionWithRSAKeyName(
            str(flo_ip), key_name)
        self.execute_command_disk_create(
            ssh, str(flo_ip), [volumes_part], [mount_point])
        self.execute_command_disk_mount(
            ssh, str(flo_ip), [volumes_part], [mount_point])
        self.addCustomfilesOnLinuxVM(ssh, mount_point, file_count)
        ssh.close()

    def calcmd5sum(self, flip, keyname, mount_point):
        ssh = self.SshRemoteMachineConnectionWithRSAKeyName(str(flip), keyname)
        mdsum = self.calculatemmd5checksum(ssh, mount_point)
        ssh.close()
        return mdsum

    def multiple_workloads(self, vms):
        wls = {}
        wln = int(len(vms) / 3)
        vmscopy = []
        vmscopy = [*vms]
        LOG.debug("\nvms : {}\n".format(vms))

        l1 = [vmscopy[i:i + 3] for i in range(0, len(vmscopy), 3)]
        LOG.debug(l1)
        i = 0
        for each in l1:
            i += 1
            workload_id = self.workload_create(
                each, tvaultconf.parallel, workload_cleanup=True)
            LOG.debug("Workload ID: " + str(workload_id))
            if(workload_id is not None):
                self.wait_for_workload_tobe_available(workload_id)
                if(self.getWorkloadStatus(workload_id) == "available"):
                    reporting.add_test_step(
                        "Create workload-{}".format(i), tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Create workload-{}".format(i), tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                    "Create workload-{}".format(i), tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("Workload creation failed")
            wls[workload_id] = []
            for vm in each:
                wls[workload_id].append([vm, vms[vm]])
        return(wls)

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_functional(self):
        try:
            ### VM and Workload ###
            reporting.add_test_script(
                'tempest.api.workloadmgr.test_functional_oneclick_restore')
            status = 0
            deleted = 0
            vm_count = tvaultconf.vm_count
            key_pairs = self.create_kps(int(vm_count / 3))
            LOG.debug("\nKey pairs : {}\n".format(key_pairs))
            sec_groups = self.create_sec_groups(int(vm_count / 3))
            LOG.debug("\nSecurity Groups: {}\n".format(sec_groups))
            vms, boot_vols = self.multiple_vms(vm_count, key_pairs, sec_groups)
            LOG.debug("\nVMs : {}\n".format(vms))
            LOG.debug("\nBoot volumes : {}\n".format(boot_vols))
            vms = self.attach_vols(vms)
            LOG.debug("\nVolumes attached : {}\n".format(vms))
            mdsums_original = self.fill_data(vms)
            LOG.debug("\nMD5 sums before snapshots : {}\n".format(
                mdsums_original))
            wls = self.multiple_workloads(vms)
            LOG.debug("\nWorkloads created : {}\n".format(wls))

            ### Full snapshot ###

            fullsnaps = {}
            i = 0
            for workload_id in wls:
                i += 1
                snapshot_id = self.workload_snapshot(
                    workload_id, True, snapshot_cleanup=True)
                time.sleep(5)
                self.wait_for_workload_tobe_available(workload_id)
                if(self.getSnapshotStatus(workload_id, snapshot_id) == "available"):
                    reporting.add_test_step(
                        "Create full snapshot-{}".format(i), tvaultconf.PASS)
                    LOG.debug("Full snapshot available!!")
                else:
                    reporting.add_test_step(
                        "Create full snapshot-{}".format(i), tvaultconf.FAIL)
                    raise Exception("Snapshot creation failed")

                fullsnaps[workload_id] = snapshot_id

            LOG.debug("\nFull snapshot ids : {}\n".format(fullsnaps))

            ### One-click Restore ###

            self.delete_vms([*vms])
            time.sleep(60)
            deleted = 1

            restores = {}
            i = 0

            mdsums_oc = {}
            instances_details = {}
            workloads = wls.items()
            for workload in workloads:
                i += 1
                instance_details = []
                wid = workload[0]
                snapshotid = fullsnaps[wid]
                wlvms = workload[1]

                # Triggger one click restore #

                restore_id = self.snapshot_restore(
                    wid, snapshotid, restore_cleanup=True)

                self.wait_for_snapshot_tobe_available(wid, snapshotid)
                if(self.getRestoreStatus(wid, snapshotid, restore_id) == "available"):
                    reporting.add_test_step(
                        "Oneclick-{}".format(i), tvaultconf.PASS)
                    LOG.debug('Oneclick restore passed')
                else:
                    reporting.add_test_step(
                        "Oneclick restore-{}".format(i), tvaultconf.FAIL)
                    LOG.debug('Oneclick restore failed')
                    raise Exception("Oneclick restore failed")

                restores[restore_id] = [wid, snapshotid]

                restored_vms = self.get_restored_vm_list(restore_id)
                vmdetails = {}
                restore_details = self.getRestoreDetails(restore_id)[
                    'instances']
                for arestore in restore_details:
                    vmdetails[arestore['id']
                              ] = arestore['metadata']['instance_id']

                LOG.debug("\nRestored vms : {}\n".format(restored_vms))
                volumes_parts = ["/dev/vdb", "/dev/vdc", "/dev/vdd"]
                mount_points = ["mount_data_a", "mount_data_b", "mount_data_c"]
                for rvm in restored_vms:
                    mdsum = ""
                    fip = ""
                    j = 0
                    rvmvols = self.get_attached_volumes(rvm)
                    LOG.debug("\nrvmvols : {}\n".format(rvmvols))
                    if len(rvmvols) > 0:
                        for rvol in rvmvols:
                            if self.volumes_client.show_volume(
                                rvol)['volume']['bootable'] == 'true':
                                rvmvols.remove(rvol)
                            else:
                                pass
                    if len(rvmvols) > 0:
                        int_net_name = self.get_net_name(
                            CONF.network.internal_network_id)
                        fip = self.get_vm_details(
                            rvm)['server']['addresses'][int_net_name][1]['addr']
                        key = self.get_vm_details(rvm)['server']['key_name']
                        for rvolume in rvmvols:
                            LOG.debug(
                                "\nrvolume : {} & j {}\n".format(rvolume, j))
                            ssh = self.SshRemoteMachineConnectionWithRSAKeyName(
                                str(fip), key)
                            self.execute_command_disk_mount(
                                ssh, str(fip), [
                                    volumes_parts[j]], [
                                    mount_points[j]])
                            ssh.close()
                            mdsum = mdsum + \
                                self.calcmd5sum(fip, key, mount_points[j])
                            j += 1
                            mdsums_oc[vmdetails[rvm]] = mdsum
                    else:
                        pass

            LOG.debug("MD5SUMS before restore")
            LOG.debug(mdsums_original)
            LOG.debug("MD5SUMS after restore")
            LOG.debug(mdsums_oc)

            if operator.eq(mdsums_original, mdsums_oc):
                LOG.debug("***MDSUMS MATCH***")
                reporting.add_test_step("Md5 Verification", tvaultconf.PASS)
                status = 1
                reporting.set_test_script_status(tvaultconf.PASS)
                reporting.test_case_to_write()
            else:
                LOG.debug("***MDSUMS DON'T MATCH***")
                reporting.add_test_step("Md5 Verification", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            if deleted == 0:
                try:
                    self.delete_vms([*vms])
                except BaseException:
                    pass
            if status != 1:
                reporting.set_test_script_status(tvaultconf.FAIL)
                reporting.test_case_to_write()
