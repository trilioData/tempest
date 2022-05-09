import json
import os
import sys
import time

import yaml

from oslo_log import log as logging

from tempest import config
from tempest import reporting
from tempest import tvaultconf
from tempest import test
from tempest.api.workloadmgr import base
from tempest.lib import decorators
from tempest import command_argument_string
from tempest.util import cli_parser
from tempest.util import query_data

sys.path.append(os.getcwd())

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    @test.pre_req({'type': 'network_topology'})
    @decorators.attr(type='workloadmgr_api')
    def test_1_network_restore_api(self):
        try:
            reporting.add_test_script(str(__name__)+"_full_snapshot_api")
            if self.exception != "":
                LOG.debug("pre req failed")
                raise Exception(str(self.exception))
            LOG.debug("pre req completed")

            global workload_id
            global snapshot_ids
            global instance_details
            global nt_bf, nt_bf_1
            global sbnt_bf, sbnt_bf_1
            global rt_bf, rt_bf_1
            global intf_bf, intf_bf_1
            global vm_details_bf, vm_details_bf_1
            workload_id = self.workload_id
            snapshot_ids = self.snapshot_ids
            instance_details = self.instance_details
            nt_bf, nt_bf_1 = self.nt_bf, self.nt_bf_1
            sbnt_bf, sbnt_bf_1 = self.sbnt_bf, self.sbnt_bf_1
            rt_bf, rt_bf_1 = self.rt_bf, self.rt_bf_1
            intf_bf, intf_bf_1 = self.intf_bf, self.intf_bf_1
            vm_details_bf, vm_details_bf_1 = self.vm_details_bf, \
                    self.vm_details_bf_1

            snapshot_id = snapshot_ids[0]
            restore_id = self.snapshot_selective_restore(
                workload_id,
                snapshot_id,
                restore_name=tvaultconf.restore_name,
                instance_details=instance_details,
                network_restore_flag=True,
                restore_cleanup=True)

            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            if(self.getRestoreStatus(workload_id, snapshot_id, restore_id) ==\
                    "available"):
                reporting.add_test_step(
                    "Selective restore of full snapshot with network restore", 
                    tvaultconf.PASS)
            else:
                raise Exception(
                    "Selective restore of full snapshot with network restore failed")

            nt_af, sbnt_af, rt_af, intf_af = self.get_topology_details()
            LOG.debug(
                    "Interface details before and after restore: {0}, {1}".format(
                        intf_bf, intf_af))

            vm_details_af = {}
            restored_vms = self.get_restored_vm_list(restore_id)
            for vm in restored_vms:
                vm_details = self.get_vm_details(vm)['server']
                vm_details_af[vm_details['name'].replace(
                    'restored_instance', '')] = vm_details

            self.verify_network_restore(nt_bf, nt_af, sbnt_bf, sbnt_af, rt_bf,
                    rt_af, vm_details_bf, vm_details_af, test_type='API')

            for rvm in restored_vms:
                self.delete_vm(rvm)
            self.delete_network_topology()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_2_network_restore_cli(self):
        try:
            reporting.add_test_script(str(__name__)+"_full_snapshot_cli")
            snapshot_id = snapshot_ids[0]
            network_restore_cmd = command_argument_string.network_restore + snapshot_id
            rc = cli_parser.cli_returncode(network_restore_cmd)
            if rc != 0:
                reporting.add_test_step(
                    "Execute restore-network-topology command",
                    tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute restore-network-topology command",
                    tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            restore_id = query_data.get_snapshot_restore_id(snapshot_id)
            if(self.getRestoreStatus(workload_id, snapshot_id, restore_id) == "available"):
                reporting.add_test_step(
                    "Network topology restore from CLI", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Network topology restore from CLI", tvaultconf.FAIL)
                raise Exception(
                    "Network topology restore from CLI failed")

            nt_af, sbnt_af, rt_af, intf_af = self.get_topology_details()
            LOG.debug(
                    "Interface details before and after restore: {0}, {1}".format(
                        intf_bf, intf_af))

            vm_details_af = {}
            restored_vms = self.get_restored_vm_list(restore_id)
            for vm in restored_vms:
                vm_details = self.get_vm_details(vm)['server']
                vm_details_af[vm_details['name'].replace(
                    'restored_instance', '')] = vm_details

            self.verify_network_restore(nt_bf, nt_af, sbnt_bf, sbnt_af, rt_bf,
                    rt_af, vm_details_bf, vm_details_af, test_type='CLI')

            for rvm in restored_vms:
                self.delete_vm(rvm)
            self.delete_network_topology()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_3_network_restore_api(self):
        try:
            reporting.add_test_script(str(__name__)+"_incremental_snapshot_api")
            snapshot_id = snapshot_ids[1]
            restore_id = self.snapshot_selective_restore(
                workload_id,
                snapshot_id,
                restore_name=tvaultconf.restore_name,
                instance_details=instance_details,
                network_restore_flag=True,
                restore_cleanup=True)

            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            if(self.getRestoreStatus(workload_id, snapshot_id, restore_id) ==\
                    "available"):
                reporting.add_test_step(
                    "Selective restore of incremental snapshot with network restore",
                    tvaultconf.PASS)
            else:
                raise Exception(
                    "Selective restore of incremental snapshot with network restore failed")

            nt_af, sbnt_af, rt_af, intf_af = self.get_topology_details()
            LOG.debug(
                    "Interface details before and after restore: {0}, {1}".format(
                        intf_bf_1, intf_af))

            vm_details_af = {}
            restored_vms = self.get_restored_vm_list(restore_id)
            for vm in restored_vms:
                vm_details = self.get_vm_details(vm)['server']
                vm_details_af[vm_details['name'].replace(
                    'restored_instance', '')] = vm_details

            self.verify_network_restore(nt_bf_1, nt_af, sbnt_bf_1, sbnt_af,
                    rt_bf_1, rt_af, vm_details_bf_1, vm_details_af,
                    test_type='API')

            for rvm in restored_vms:
                self.delete_vm(rvm)
            self.delete_network_topology()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_4_network_restore_cli(self):
        try:
            reporting.add_test_script(str(__name__)+"_incremental_snapshot_cli")
            snapshot_id = snapshot_ids[1]
            network_restore_cmd = command_argument_string.network_restore + snapshot_id
            rc = cli_parser.cli_returncode(network_restore_cmd)
            if rc != 0:
                reporting.add_test_step(
                    "Execute restore-network-topology command",
                    tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute restore-network-topology command",
                    tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            restore_id = query_data.get_snapshot_restore_id(snapshot_id)
            if(self.getRestoreStatus(workload_id, snapshot_id, restore_id) == "available"):
                reporting.add_test_step(
                    "Network topology restore from CLI", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Network topology restore from CLI", tvaultconf.FAIL)
                raise Exception(
                    "Network topology restore from CLI failed")

            nt_af, sbnt_af, rt_af, intf_af = self.get_topology_details()
            LOG.debug(
                    "Interface details before and after restore: {0}, {1}".format(
                        intf_bf_1, intf_af))

            vm_details_af = {}
            restored_vms = self.get_restored_vm_list(restore_id)
            for vm in restored_vms:
                vm_details = self.get_vm_details(vm)['server']
                vm_details_af[vm_details['name'].replace(
                    'restored_instance', '')] = vm_details

            self.verify_network_restore(nt_bf_1, nt_af, sbnt_bf_1, sbnt_af,
                    rt_bf_1, rt_af, vm_details_bf_1, vm_details_af,
                    test_type='CLI')

            for rvm in restored_vms:
                self.delete_vm(rvm)
            self.delete_network_topology()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_5_network_restore_cli_workload_reassign(self):
        try:
            reporting.add_test_script(str(__name__) + "_full_snapshot_cli")
            tenant_id = CONF.identity.tenant_id
            tenant_id_1 = CONF.identity.tenant_id_1

            user_id = CONF.identity.user_id

            rc = self.workload_reassign(tenant_id_1, workload_id, user_id)
            if rc == 0:
                LOG.debug("Workload reassign from tenant 1 to tenant 2 passed")
                reporting.add_test_step(
                    "Workload reassign from tenant 1 to 2", tvaultconf.PASS)
            else:
                LOG.error("Workload reassign from tenant 1 to 2 failed")
                reporting.add_test_step(
                    "Workload reassign from tenant 1 to 2", tvaultconf.FAIL)

            snapshot_id = snapshot_ids[0]

            payload = {'instance_details': instance_details,
                       'restore_topology': True}

            restore_json = json.dumps(payload)
            LOG.debug("restore.json for selective restore: " + str(restore_json))
            # Create Restore.json
            with open(tvaultconf.restore_filename, 'w') as f:
                f.write(str(yaml.safe_load(restore_json)))
            # Create in-place restore with CLI command
            restore_command = command_argument_string.selective_restore + \
                              str(tvaultconf.restore_filename) + " " + str(snapshot_id)
            LOG.debug("command for selective restore: " + str(restore_command))
            rc = cli_parser.cli_returncode(restore_command)
            if rc != 0:
                reporting.add_test_step(
                    "Execute restore-network-topology command",
                    tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute restore-network-topology command",
                    tvaultconf.PASS)
                LOG.debug("Command executed correctly - " + str(rc))

            self.wait_for_snapshot_tobe_available(workload_id, snapshot_id)
            restore_id = query_data.get_snapshot_restore_id(snapshot_id)
            if (self.getRestoreStatus(workload_id, snapshot_id, restore_id) == "available"):
                reporting.add_test_step(
                    "Network topology restore from CLI", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Network topology restore from CLI", tvaultconf.FAIL)
                raise Exception(
                    "Network topology restore from CLI failed")

            nt_af, sbnt_af, rt_af, intf_af = self.get_topology_details()
            LOG.debug(
                "Interface details before and after restore: {0}, {1}".format(
                    intf_bf, intf_af))

            vm_details_af = {}
            restored_vms = self.get_restored_vm_list(restore_id)
            for vm in restored_vms:
                vm_details = self.get_vm_details(vm)['server']
                vm_details_af[vm_details['name'].replace(
                    'restored_instance', '')] = vm_details

            self.verify_network_restore(nt_bf, nt_af, sbnt_bf, sbnt_af, rt_bf,
                                        rt_af, vm_details_bf, vm_details_af, test_type='CLI')

            for rvm in restored_vms:
                self.delete_vm(rvm)
            self.delete_network_topology()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    # def test_6_cleanup(self):
    #     try:
    #         for snapshot_id in snapshot_ids:
    #             self.addCleanup(self.snapshot_delete, workload_id, snapshot_id)
    #         self.addCleanup(self.workload_delete, workload_id)
    #     except Exception as e:
    #         LOG.error("Exception: " + str(e))

