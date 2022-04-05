import os
import sys
import time

from oslo_log import log as logging

from tempest import config
from tempest import reporting
from tempest.api.workloadmgr import base
from tempest.lib import decorators

sys.path.append(os.getcwd())

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    @decorators.attr(type='workloadmgr_api')
    def test_image_restore(self):
        try:
            reporting.add_test_script(str(__name__))
            self.image_id = self.create_image()
            LOG.debug(f"Image ID: {self.image_id}")
            self.kp = self.create_key_pair()
            self.vm_id = self.create_vm(image_id=self.image_id,
                                key_pair=self.kp)
            LOG.debug(f"VM ID: {self.vm_id}")
            self.volumes = []
            fip = self.get_floating_ips()
            LOG.debug("\nAvailable floating ips are {}: \n".format(fip))
            if len(fip) < 2:
                raise Exception("Floating ips unavailable")
            self.set_floating_ip(fip[0], self.vm_id)

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            self.install_qemu(ssh)
            self.addCustomfilesOnLinuxVM(ssh, "/opt", 2)
            md5sums_before_full = self.calculatemmd5checksum(ssh, "/opt")
            LOG.debug(f"md5sums_before_full: {md5sums_before_full}")
            ssh.close()

            self.reboot_instance(self.vm_id)
            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            md5sums_after_reboot = self.calculatemmd5checksum(ssh, "/opt")
            LOG.debug(f"md5sums_after_reboot: {md5sums_after_reboot}")
            ssh.close()

            if md5sums_before_full == md5sums_after_reboot:
                reporting.add_test_step(
                        "File present after reboot", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                        "File not present after reboot", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            # Create workload with API
            try:
                self.wid = self.workload_create([self.vm_id],
                        tvaultconf.workload_type_id)
                LOG.debug(f"Workload ID: {self.wid}")
            except Exception as e:
                LOG.error(f"Exception: {e}")
                raise Exception("Create workload")
            if(self.wid is not None):
                self.wait_for_workload_tobe_available(self.wid)
                self.workload_status = self.getWorkloadStatus(self.wid)
                if(self.workload_status == "available"):
                    reporting.add_test_step("Create workload", tvaultconf.PASS)
                else:
                    raise Exception("Create workload")
            else:
                raise Exception("Create workload")

            #Create full snapshot
            self.snapshot_id = self.workload_snapshot(self.wid, True)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                    self.snapshot_id)
            if(self.snapshot_status == "available"):
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
            else:
                raise Exception("Create full snapshot")

            #selective restore
            rest_details = {}
            rest_details['rest_type'] = 'selective'
            rest_details['network_id'] = CONF.network.internal_network_id
            rest_details['subnet_id'] = self.get_subnet_id(
                CONF.network.internal_network_id)
            rest_details['instances'] = {self.vm_id: self.volumes}

            payload = self.create_restore_json(rest_details)
            # Trigger selective restore of full snapshot
            restore_id_1 = self.snapshot_selective_restore(
                self.wid, self.snapshot_id,
                restore_name="selective_restore_full_snap",
                instance_details=payload['instance_details'],
                network_details=payload['network_details'])
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id)
            if(self.getRestoreStatus(self.wid, self.snapshot_id,
                    restore_id_1) == "available"):
                reporting.add_test_step("Selective restore of full snapshot",
                        tvaultconf.PASS)
                vm_list = self.get_restored_vm_list(restore_id_1)
                LOG.debug("Restored vm(selective) ID : " + str(vm_list))
                time.sleep(60)
                self.set_floating_ip(fip[1], vm_list[0])
                LOG.debug("Floating ip assigned to selective restored vm -> " +\
                        f"{fip[1]}")
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[1])
                md5sums_after_full_selective = self.calculatemmd5checksum(ssh, "/opt")
                LOG.debug(f"md5sums_after_full_selective: {md5sums_after_full_selective}")
                ssh.close()

                if md5sums_before_full == \
                        md5sums_after_full_selective:
                    reporting.add_test_step(
                        "File present on restored instance", tvaultconf.PASS)
                else:
                    reporting.add_test_step(
                        "File not present on restored instance", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                raise Exception("Selective restore of full snapshot")
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()
