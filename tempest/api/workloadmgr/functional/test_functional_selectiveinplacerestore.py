import operator
import os
import random
import sys
import time

from oslo_log import log as logging

from tempest import config
from tempest import reporting
from tempest import tvaultconf
from tempest.api.workloadmgr import base
from tempest.lib import decorators

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
                    vm_cleanup=True)
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
                    vm_cleanup=True)
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
                self.attach_volume(volume_id, vm, attach_cleanup=True)
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
        if len(fip) > 0:
            self.set_floating_ip(str(fip[0]), vm_id, floatingip_cleanup=fipcleanup)
            return(fip[0])
        else:
            raise Exception("Floating IP unavailable")

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
                each,  workload_cleanup=True)
            LOG.debug("Workload ID: " + str(workload_id))
            if(workload_id is not None):
                self.wait_for_workload_tobe_available(workload_id)
                if(self.getWorkloadStatus(workload_id) == "available"):
                    reporting.add_test_step(
                        "Create workload-{}".format(i), tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "Create workload-{}".format(i), tvaultconf.FAIL)
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
    @decorators.attr(type='workloadmgr_api')
    def test_functional(self):
        try:

            ### VM and Workload ###
            tests = [['tempest.api.workloadmgr.test_functional_Selective-restore',
                      0], ['tempest.api.workloadmgr.test_functional_Inplace-restore', 0]]
            reporting.add_test_script(tests[0][0])
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

            # Add some more data to files on VM
            volumes_parts = ["/dev/vdb", "/dev/vdc", "/dev/vdd"]
            mount_points = ["mount_data_a", "mount_data_b", "mount_data_c"]
            for each in vms:
                if len(vms[each]) == 3:
                    ssh = self.SshRemoteMachineConnectionWithRSAKeyName(
                        str(vms[each][2]), vms[each][0])
                    i = 0
                    for each_vol in vms[each][1]:
                        self.addCustomfilesOnLinuxVM(ssh, mount_points[i], 2)
                        i += 1
                    ssh.close()
                else:
                    pass

            # Calculate md5sum after filling the data
            mdsums_original2 = {}
            for vm in [*vms]:
                mdsum = ""
                fip = ""
                j = 0
                vmvols = self.get_attached_volumes(vm)
                LOG.debug("\nvmvols : {}\n".format(vmvols))
                if len(vmvols) > 0:
                    for vol in vmvols:
                        if self.volumes_client.show_volume(
                            vol)['volume']['bootable'] == 'true':
                            vmvols.remove(vol)
                        else:
                            pass
                else:
                    pass
                if len(vmvols) > 0:
                    fip = vms[vm][2]
                    key = vms[vm][0]
                    for avolume in vmvols:
                        LOG.debug("\navolume : {} & j {}\n".format(avolume, j))
                        mdsum = mdsum + \
                            self.calcmd5sum(fip, key, mount_points[j])
                        j += 1
                        mdsums_original2[vm] = mdsum
                else:
                    pass

            ### Incremental snapshot ###

            incrsnaps = {}
            i = 0
            for workload_id in wls:
                i += 1
                incr_snapshot_id = self.workload_snapshot(
                    workload_id, False, snapshot_cleanup=True)
                time.sleep(5)
                self.wait_for_workload_tobe_available(workload_id)
                if(self.getSnapshotStatus(workload_id, incr_snapshot_id) == "available"):
                    reporting.add_test_step(
                        "Create incremental snapshot-{}".format(i), tvaultconf.PASS)
                    LOG.debug("Incremental snapshot available!!")
                else:
                    reporting.add_test_step(
                        "Create incremental snapshot-{}".format(i), tvaultconf.FAIL)
                    raise Exception("Snapshot creation failed")

                incrsnaps[workload_id] = incr_snapshot_id

            LOG.debug("\nIncremental snapshots : {}\n".format(incrsnaps))

            ### Selective Restore ###

            restores = {}
            network_details = []
            i = 0
            int_net_1_name = self.get_net_name(
                CONF.network.internal_network_id)
            LOG.debug("int_net_1_name" + str(int_net_1_name))
            int_net_1_subnets = self.get_subnet_id(
                CONF.network.internal_network_id)
            LOG.debug("int_net_1_subnet" + str(int_net_1_subnets))

            # Create network details for restore.json
            snapshot_network = {
                'id': CONF.network.internal_network_id,
                'subnet': {'id': int_net_1_subnets}
                }
            target_network = {'name': int_net_1_name,
                              'id': CONF.network.internal_network_id,
                              'subnet': {'id': int_net_1_subnets}
                              }
            network_details = [{'snapshot_network': snapshot_network,
                                'target_network': target_network}]
            LOG.debug("Network details for restore: " + str(network_details))
            LOG.debug("Snapshot id : " + str(snapshot_id))

            mdsums_sr = {}
            instances_details = {}
            workloads = wls.items()
            for workload in workloads:
                i += 1
                instance_details = []
                wid = workload[0]
                snapshotid = fullsnaps[wid]
                wlvms = workload[1]
                for vmvol in wlvms:
                    temp_vdisks_data = []
                    temp_instance_data = {}
                    vmid = vmvol[0]
                    vmname = vmid + "_selectively_restored"
                    volumes = vmvol[1][1]
                    if len(volumes) == 0:
                        temp_instance_data = {
                            'id': vmid,
                            'availability_zone': CONF.compute.vm_availability_zone,
                            'include': True,
                            'restore_boot_disk': True,
                            'name': vmname}
                        instance_details.append(temp_instance_data)
                    else:
                        for volume in volumes:
                            temp_vdisks_data.append(
                                {
                                    'id': volume,
                                    'availability_zone': CONF.volume.volume_availability_zone,
                                    'new_volume_type': CONF.volume.volume_type})
                        temp_instance_data = {
                            'id': vmid,
                            'availability_zone': CONF.compute.vm_availability_zone,
                            'include': True,
                            'restore_boot_disk': True,
                            'name': vmname,
                            'vdisks': temp_vdisks_data}
                        instance_details.append(temp_instance_data)

                LOG.debug("Instance details for restore: " +
                          str(instance_details))
                instances_details[wid] = instance_details

                # Trigger selective restore
                restore_id_1 = self.snapshot_selective_restore(
                    wid,
                    snapshotid,
                    restore_name=tvaultconf.restore_name,
                    restore_cleanup=True,
                    instance_details=instance_details,
                    network_details=network_details)
                self.wait_for_snapshot_tobe_available(wid, snapshotid)
                if(self.getRestoreStatus(wid, snapshotid, restore_id_1) == "available"):
                    reporting.add_test_step(
                        "Selective restore-{}".format(i), tvaultconf.PASS)
                    LOG.debug('selective restore passed')
                else:
                    reporting.add_test_step(
                        "Selective restore-{}".format(i), tvaultconf.FAIL)
                    LOG.debug('selective restore failed')
                    raise Exception("Selective restore failed")

                restores[restore_id_1] = [wid, snapshotid]

                restored_vms = self.get_restored_vm_list(restore_id_1)
                LOG.debug("\nRestored vms : {}\n".format(restored_vms))
                volumes_parts = ["/dev/vdb", "/dev/vdc", "/dev/vdd"]
                mount_points = ["mount_data_a", "mount_data_b", "mount_data_c"]
                for rvm in restored_vms:
                    mdsum = ""
                    fip = ""
                    j = 0
                    rvmname = self.get_vm_details(rvm)['server']['name'].replace(
                        '_selectively_restored', '')
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
                        try:
                            fip = self.assign_floating_ips(rvm, True)
                            key = vms[rvmname][0]
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
                                mdsums_sr[rvmname] = mdsum
                        except Exception as e:
                            reporting.add_test_step(str(e), tvaultconf.FAIL)
                    else:
                        pass

            LOG.debug("MD5SUMS before restore")
            LOG.debug(mdsums_original)
            LOG.debug("MD5SUMS after restore")
            LOG.debug(mdsums_sr)

            if operator.eq(mdsums_original, mdsums_sr):
                LOG.debug("***MDSUMS MATCH***")
                reporting.add_test_step("Md5 Verification", tvaultconf.PASS)
                tests[0][1] = 1
                reporting.set_test_script_status(tvaultconf.PASS)
                reporting.test_case_to_write()
            else:
                LOG.debug("***MDSUMS DON'T MATCH***")
                reporting.add_test_step("Md5 Verification", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                reporting.test_case_to_write()

            ### In-place restore ###

            reporting.add_test_script(tests[1][0])
            k = 1
            workloads = wls.items()
            for workload in workloads:
                wid = workload[0]
                incrsnapid = incrsnaps[wid]

                payload = {
                    "restore": {
                        "options": {
                            'name': "inplace-{}".format(wid),
                            'description': "",
                            'type': 'openstack',
                                    'oneclickrestore': False,
                            'restore_type': 'inplace',
                            'openstack': {
                                'instances': instances_details[wid],
                                'networks_mapping': {'networks': []}
                                }
                            }
                        }
                    }
                #self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
                resp, body = self.wlm_client.client.post(
                    "/workloads/" + wid + "/snapshots/" + incrsnapid + "/restores", json=payload)
                restore_id_2 = body['restore']['id']
                LOG.debug(
                    "#### workloadid: %s ,snapshot_id: %s , restore_id: %s , operation: snapshot_restore" %
                    (workload_id, incrsnapid, restore_id_2))
                LOG.debug("Response:" + str(resp.content))
                if(resp.status_code != 202):
                    resp.raise_for_status()
                LOG.debug(
                    'Restore of snapshot %s scheduled succesffuly' %
                    incrsnapid)
                if(tvaultconf.cleanup):
                    self.wait_for_snapshot_tobe_available(
                        workload_id, incrsnapid)
                    self.restored_vms = self.get_restored_vm_list(restore_id_2)
                    self.restored_volumes = self.get_restored_volume_list(
                        restore_id_2)
                    self.addCleanup(self.restore_delete,
                                    workload_id, incrsnapid, restore_id_2)
                    self.addCleanup(self.delete_restored_vms,
                                    self.restored_vms, self.restored_volumes)

                self.wait_for_snapshot_tobe_available(wid, incrsnapid)
                if(self.getRestoreStatus(wid, incrsnapid, restore_id_2) == "available"):
                    reporting.add_test_step(
                        "In-place restore-{}".format(k), tvaultconf.PASS)
                    LOG.debug('In-place restore passed')
                else:
                    reporting.add_test_step(
                        "In-place restore-{}".format(k), tvaultconf.FAIL)
                    LOG.debug('In-place restore failed')
                    raise Exception("In-place restore failed")
                k += 1
                restores[restore_id_2] = [wid, incrsnapid]

                mdsums_ipr = {}
                restored_vms = self.get_restored_vm_list(restore_id_2)
                LOG.debug("\nRestored vms : {}\n".format(restored_vms))
                for rvm in [*vms]:
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
                    else:
                        pass
                    if len(rvmvols) > 0:
                        fip = vms[rvm][2]
                        key = vms[rvm][0]
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
                            mdsums_ipr[rvm] = mdsum
                    else:
                        pass

            LOG.debug("MD5SUMS before restore")
            LOG.debug(mdsums_original2)
            LOG.debug("MD5SUMS after restore")
            LOG.debug(mdsums_ipr)

            if operator.eq(mdsums_original2, mdsums_ipr):
                LOG.debug("***MDSUMS MATCH***")
                reporting.add_test_step("Md5 Verification", tvaultconf.PASS)
                tests[1][1] = 1
                reporting.set_test_script_status(tvaultconf.PASS)
                reporting.test_case_to_write()

            else:
                LOG.debug("***MDSUMS DON'T MATCH***")
                reporting.add_test_step("Md5 Verification", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            for test in tests:
                if test[1] != 1:
                    reporting.add_test_script(test[0])
                    reporting.set_test_script_status(tvaultconf.FAIL)
                    reporting.test_case_to_write()
