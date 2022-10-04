import os
import sys
import time

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

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()


    @decorators.attr(type='workloadmgr_api')
    def test_user_data_backup_restore (self):
        reporting.add_test_script(str(__name__))
        try:
            self.kp = self.create_key_pair(tvaultconf.key_pair_name)
            self.vm_id = self.create_vm(
                user_data=tvaultconf.user_data_vm,
                key_pair=self.kp)
            self.volumes = []

            fip = self.get_floating_ips()
            LOG.debug("\nAvailable floating ips are {}: \n".format(fip))
            if len(fip) < 2:
                raise Exception("Floating ips unavailable")
            self.set_floating_ip(fip[0], self.vm_id)

            ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[0])
            userdata_before = self.executecurlonvm(ssh,tvaultconf.curl_to_get_userdata)
            ssh.close()

            # Create workload with API
            try:
                self.wid = self.workload_create([self.vm_id],
                                                tvaultconf.workload_type_id)
                LOG.debug("Workload ID: " + str(self.wid))
            except Exception as e:
                LOG.error(f"Exception: {e}")
                raise Exception("Create workload")
            if (self.wid is not None):
                self.wait_for_workload_tobe_available(self.wid)
                self.workload_status = self.getWorkloadStatus(self.wid)
                if (self.workload_status == "available"):
                    reporting.add_test_step("Create workload" , tvaultconf.PASS)

                else:
                    raise Exception("Create workload")
            else:
                raise Exception("Create workload")

            self.snapshot_id = self.workload_snapshot(self.wid, True)
            self.wait_for_workload_tobe_available(self.wid)
            self.snapshot_status = self.getSnapshotStatus(self.wid,
                                                          self.snapshot_id)
            if (self.snapshot_status == "available"):
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
            else:
                raise Exception("Create full snapshot")

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
            if (self.getRestoreStatus(self.wid, self.snapshot_id,
                                      restore_id_1) == "available"):
                reporting.add_test_step("Selective restore of full snapshot",
                                        tvaultconf.PASS)
                vm_list = self.get_restored_vm_list(restore_id_1)
                LOG.debug("Restored vm(selective) ID : " + str(vm_list))
                time.sleep(60)
                self.set_floating_ip(fip[2], vm_list[0])
                LOG.debug("Floating ip assigned to selective restored vm -> " + \
                          f"{fip[2]}")
                ssh = self.SshRemoteMachineConnectionWithRSAKey(fip[2])
                userdata_after = self.executecurlonvm(ssh,tvaultconf.curl_to_get_userdata)
                ssh.close()

                if userdata_before == userdata_after:
                    LOG.debug("***User data MATCH***")
                    reporting.add_test_step(
                        "User data Verification", tvaultconf.PASS)
                else:
                    LOG.debug("***User data DON'T MATCH***")
                    reporting.add_test_step(
                        "User data Verification", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step("Selective restore of full snapshot",
                                        tvaultconf.FAIL)

            reporting.test_case_to_write()
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
