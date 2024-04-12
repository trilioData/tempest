import os
import sys

from oslo_log import log as logging

from tempest import config
from tempest import command_argument_string
from tempest import reporting
from tempest import tvaultconf
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

    @decorators.attr(type='workloadmgr_cli')
    def test_01_secgroup(self):
        reporting.add_test_script(str(__name__) + "_from_other_project")
        try:
            self.secgrp_name = "secgroup-6007"
            self.secgrp_id = self.create_security_group(self.secgrp_name, 
                                                        "secgroup-test", 
                                                        CONF.identity.tenant_id_1)
            self.add_security_group_rule(self.secgrp_id, ip_proto="TCP")

            self.volumes = []
            self.vm_id = self.create_vm()
            self.add_security_group_to_instance(self.vm_id, self.secgrp_id)

            self.vm_data = self.get_vm_details(self.vm_id)
            self.vm_secgrps = [x['name'] for x in self.vm_data['server']['security_groups']]
            LOG.debug(f"Security groups of VM: {self.vm_secgrps}")
            if self.secgrp_name in self.vm_secgrps:
                reporting.add_test_step(
                        "Security group from other project added to instance",
                        tvaultconf.PASS)
            else:
                raise Exception(
                        "Security group from other project not added to instance")

            self.wid = self.workload_create([self.vm_id])
            LOG.debug("Workload ID: " + str(self.wid))
            if(self.wid is not None):
                self.wait_for_workload_tobe_available(self.wid)
                if(self.getWorkloadStatus(self.wid) == "available"):
                    reporting.add_test_step("Create workload", tvaultconf.PASS)
                else:
                    raise Exception("Create workload")
            else:
                raise Exception("Create workload")

            self.snapshot_id = self.workload_snapshot(
                self.wid, True, tvaultconf.snapshot_name)
            LOG.debug("Snapshot ID: " + str(self.snapshot_id))

            self.wait_for_workload_tobe_available(self.wid)
            if(self.getSnapshotStatus(self.wid, self.snapshot_id) == \
                    "available"):
                reporting.add_test_step("Create full snapshot", 
                                        tvaultconf.PASS)
            else:
                raise Exception("Create full snapshot failed")

            #selective restore
            rest_details = {}
            rest_details['rest_type'] = 'selective'
            rest_details['network_id'] = CONF.network.internal_network_id
            rest_details['subnet_id'] = self.get_subnet_id(
                CONF.network.internal_network_id)
            rest_details['instances'] = {self.vm_id: self.volumes}

            payload = self.create_restore_json(rest_details)
            # Trigger selective restore of full snapshot
            self.restore_id = self.snapshot_selective_restore(
                self.wid, self.snapshot_id,
                restore_name="selective_restore_full_snap",
                instance_details=payload['instance_details'],
                network_details=payload['network_details'])
            self.wait_for_snapshot_tobe_available(self.wid, self.snapshot_id)
            if(self.getRestoreStatus(self.wid, self.snapshot_id,
                    self.restore_id) == "available"):
                reporting.add_test_step("Selective restore of full snapshot",
                        tvaultconf.PASS)
                vm_list = self.get_restored_vm_list(self.restore_id)
                LOG.debug("Restored vm(selective) ID : " + str(vm_list))

                self.vm_data = self.get_vm_details(vm_list[0])
                self.vm_secgrps = [x['name'] for x in self.vm_data['server']\
                        ['security_groups']]
                LOG.debug(f"Security groups of VM: {self.vm_secgrps}")
                if self.secgrp_name in self.vm_secgrps:
                    reporting.add_test_step("Security group from other "\
                            "project added to restored instance", 
                                            tvaultconf.PASS)
                else:
                    raise Exception("Security group from other project "\
                            "not added to restored instance")

            else:
                reporting.add_test_step("Selective restore of full snapshot",
                        tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.add_test_step(str(e), tvaultconf.FAIL)

        finally:
            reporting.test_case_to_write()
