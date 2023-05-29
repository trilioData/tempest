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
from tempest import command_argument_string
from tempest.util import cli_parser
from tempest.util import query_data

sys.path.append(os.getcwd())

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']
    workload_id = None
    snapshot_id = None
    vm_id = None
    volume_id = None
    workload_name = None

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    @test.pre_req({'type': 'basic_workload'})
    @decorators.attr(type='workloadmgr_api')
    def test_1_get_audit_log(self):
        try:
            reporting.add_test_script(str(__name__) + "_get_audit_log")
            if self.exception != "":
                LOG.debug("pre req failed")
                reporting.add_test_step(str(self.exception), tvaultconf.FAIL)
                raise Exception(str(self.exception))

            global vm_id
            global volume_id
            global workload_id
            global workload_name
            global snapshot_id

            workload_id = self.wid
            workload_name = self.workload_name
            vm_id = self.vm_id
            volume_id = self.volume_id

            LOG.debug("workload is:" + str(workload_id))
            LOG.debug("workload is:" + str(workload_name))
            LOG.debug("vm id: " + str(vm_id))
            LOG.debug("volume id: " + str(volume_id))

            snapshot_id = self.workload_snapshot(workload_id, True)

            wc = self.wait_for_snapshot_tobe_available(
                workload_id, snapshot_id)
            if (str(wc) == "available"):
                reporting.add_test_step("Full snapshot", tvaultconf.PASS)
                LOG.debug("Workload snapshot successfully completed")
                self.created = True
            else:
                if (str(wc) == "error"):
                    pass
            if (self.created == False):
                reporting.add_test_step("Full snapshot", tvaultconf.FAIL)
                raise Exception("Workload snapshot did not get created")

            audit_log = self.getAuditLog()
            LOG.debug("Audit logs are : " + str(audit_log))
            wkld_name = tvaultconf.workload_name
            if len(audit_log) >= 0 and str(audit_log).find(wkld_name):
                LOG.debug("audit log API returns log successfully")
                reporting.add_test_step("Audit Log", tvaultconf.PASS)
            else:
                LOG.debug("audit log API does not return anything")
                reporting.add_test_step("Audit Log", tvaultconf.FAIL)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_2_get_storage_details(self):
        try:
            reporting.add_test_script(str(__name__) + "_get_storage_details")

            storage_usage = self.getStorageUsage()
            LOG.debug("Storage details are : " + str(storage_usage))
            wkld_name = workload_name
            if len(
                storage_usage) > 0 and storage_usage[0]['total_capacity_humanized'] is not None:
                LOG.debug("storage details returns successfully")
                reporting.add_test_step("Storage Details ", tvaultconf.PASS)
            else:
                LOG.debug("storage detailsAPI does not return anything")
                reporting.add_test_step("Storage Details", tvaultconf.FAIL)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_3_get_tenant_details(self):
        try:
            reporting.add_test_script(str(__name__) + "_get_tenant_details")

            tenant_usage = self.getTenantUsage()
            LOG.debug("Tenant details are : " + str(tenant_usage))
            wkld_name = workload_name
            if len(tenant_usage) > 0:
                LOG.debug("Tenant details returns successfully")
                reporting.add_test_step("Tenant Details ", tvaultconf.PASS)
            else:
                LOG.debug("Tenant details API does not return anything")
                reporting.add_test_step("Tenant Details", tvaultconf.FAIL)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_4_wlm_service(self):
        try:
            reporting.add_test_script(str(__name__) + "_disable_enable_wlm_service")
            wlm_nodes = self.get_wlm_nodes()
            node_names = [x['node'] for x in wlm_nodes]
            LOG.debug(f"node_names: {node_names}")

            wlm_disable = command_argument_string.service_disable +\
                    node_names[0]
            out = (cli_parser.cli_output(wlm_disable)).replace('\n', '')
            LOG.debug(f"CLI output: {out}")

            expected_resp = tvaultconf.service_disable_msg + node_names[0]
            if out == expected_resp:
                reporting.add_test_step("Disable WLM service", tvaultconf.PASS)
            else:
                reporting.add_test_step("Disable WLM service", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            db_data = query_data.get_service_status(node_names[0])
            LOG.debug(f"Data returned from DB: {db_data}")
            if db_data[0] == 1 and \
                    db_data[1].find(tvaultconf.wlm_disable_reason) != -1:
                reporting.add_test_step("Verification with DB", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verification with DB", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            wlm_nodes = self.get_wlm_nodes()
            for node in wlm_nodes:
                if node['node'] == node_names[0]:
                    if node['status'] == 'Down':
                        reporting.add_test_step("Node status verification", tvaultconf.PASS)
                    else:
                        reporting.add_test_step("Node status verification", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)
                    break

            wlm_enable = command_argument_string.service_enable +\
                    node_names[0]
            out = (cli_parser.cli_output(wlm_enable)).replace('\n', '')
            LOG.debug(f"CLI output: {out}")

            expected_resp = tvaultconf.service_enable_msg + node_names[0]
            if out == expected_resp:
                reporting.add_test_step("Enable WLM service", tvaultconf.PASS)
            else:
                reporting.add_test_step("Enable WLM service", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            db_data = query_data.get_service_status(node_names[0])
            LOG.debug(f"Data returned from DB: {db_data}")
            if db_data[0] == 0 and not db_data[1]:
                reporting.add_test_step("Verification with DB", tvaultconf.PASS)
            else:
                reporting.add_test_step("Verification with DB", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            wlm_nodes = self.get_wlm_nodes()
            for node in wlm_nodes:
                if node['node'] == node_names[0]:
                    if node['status'] == 'Up':
                        reporting.add_test_step("Node status verification", tvaultconf.PASS)
                    else:
                        reporting.add_test_step("Node status verification", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)
                    break

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_5_wlm_service(self):
        try:
            reporting.add_test_script(str(__name__) + "_disable_enable_wlm_service_non-admin-user")
            # Fetch wlm nodes list
            wlm_nodes = self.get_wlm_nodes()
            node_names = [x['node'] for x in wlm_nodes]
            LOG.debug(f"node_names: {node_names}")

            # Use non-admin credentials
            os.environ['OS_USERNAME'] = CONF.identity.nonadmin_user
            os.environ['OS_PASSWORD'] = CONF.identity.nonadmin_password

            wlm_disable = command_argument_string.service_disable +\
                    node_names[0]
            error = cli_parser.cli_error(wlm_disable)
            LOG.debug(f"Error returned from CLI: {error}")
            if error and \
                    (str(error.strip('\n')).find(
                        tvaultconf.wlm_disable_err_msg) != -1):
                reporting.add_test_step("Non-admin user unable to disable WLM service",
                        tvaultconf.PASS)
            else:
                reporting.add_test_step("Non-admin user able to disable WLM service",
                        tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            wlm_enable = command_argument_string.service_enable +\
                    node_names[0]
            error = cli_parser.cli_error(wlm_enable)
            LOG.debug(f"Error returned from CLI: {error}")
            if error and \
                    (str(error.strip('\n')).find(
                        tvaultconf.wlm_disable_err_msg) != -1):
                reporting.add_test_step("Non-admin user unable to enable WLM service",
                        tvaultconf.PASS)
            else:
                reporting.add_test_step("Non-admin user able to enable WLM service",
                        tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_6_wlm_service(self):
        try:
            reporting.add_test_script(str(__name__) + "_disable_wlm_service_all_nodes")
            node_names = []

            vm_id = self.create_vm()
            wlm_nodes = self.get_wlm_nodes()
            node_names = [x['node'] for x in wlm_nodes]
            LOG.debug(f"node_names: {node_names}")
            #Ensure all wlm nodes are enabled
            for node in node_names:
                self.update_wlm_service(node, 'enable')
            wlm_nodes = self.get_wlm_nodes()

            try:
                wid = self.workload_create([vm_id])
                LOG.debug("Workload ID: " + str(wid))
            except Exception as e:
                raise Exception(e)
            if wid:
                self.wait_for_workload_tobe_available(wid)
                workload_status = self.getWorkloadStatus(wid)
                if(workload_status == "available"):
                    reporting.add_test_step("Create workload", tvaultconf.PASS)
                else:
                    raise Exception("Create workload")
            else:
                raise Exception("Create workload")

            #Disable all wlm nodes
            for node in node_names:
                self.update_wlm_service(node, 'disable')
            wlm_nodes_after_disable = self.get_wlm_nodes()
            flag = True
            for node in wlm_nodes_after_disable:
                if node['status'].lower() != 'down':
                    flag = False
            if flag:
                reporting.add_test_step(
                        "Disable wlm-workloads service on all nodes",
                        tvaultconf.PASS)
                #Trigger snapshot
                snapshot_id = self.workload_snapshot(wid, True)
                self.wait_for_workload_tobe_available(wid)
                snapshot_data = self.getSnapshotDetails(wid, snapshot_id)
                workload_status = self.getWorkloadStatus(wid)
                if snapshot_data['status'] == 'error' and \
                        snapshot_data['error_msg'] == 'No valid host was found. ':
                    reporting.add_test_step("Unable to create snapshot",
                            tvaultconf.PASS)
                else:
                    reporting.add_test_step("Able to create snapshot",
                            tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
                if workload_status == 'available':
                    reporting.add_test_step("Workload status set to available",
                            tvaultconf.PASS)
                else:
                    reporting.add_test_step("Workload status set to available",
                            tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            else:
                reporting.add_test_step(
                        "Disable wlm-workloads service on all nodes",
                        tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            #Enable all wlm nodes
            for node in node_names:
                self.update_wlm_service(node, 'enable')
            wlm_nodes_final = self.get_wlm_nodes()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_7_wlm_service(self):
        try:
            reporting.add_test_script(str(__name__) + "_disable_wlm_service_running_snapshot")
            node_names = []
            vm_id = self.create_vm()
            wlm_nodes = self.get_wlm_nodes()

            try:
                wid = self.workload_create([vm_id])
                LOG.debug("Workload ID: " + str(wid))
            except Exception as e:
                raise Exception(e)
            if wid:
                self.wait_for_workload_tobe_available(wid)
                workload_status = self.getWorkloadStatus(wid)
                if(workload_status == "available"):
                    reporting.add_test_step("Create workload", tvaultconf.PASS)
                else:
                    raise Exception("Create workload")
            else:
                raise Exception("Create workload")

            #Trigger snapshot
            snapshot_id = self.workload_snapshot(wid, True)
            if snapshot_id:
                reporting.add_test_step("Trigger snapshot", tvaultconf.PASS)
            else:
                raise Exception("Trigger snapshot")
            time.sleep(20)
            snapshot_data = self.getSnapshotDetails(wid, snapshot_id)

            #Disable wlm-workloads service on specific host on which
            #snapshot is running
            if self.update_wlm_service(snapshot_data['host'], 'disable'):
                reporting.add_test_step("Disable wlm service on snapshot host",
                        tvaultconf.PASS)
            else:
                reporting.add_test_step("Disable wlm service on snapshot host",
                        tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            self.wait_for_workload_tobe_available(wid)
            snapshot_status = self.getSnapshotStatus(wid, snapshot_id)
            if snapshot_status == 'available':
                reporting.add_test_step("Snapshot creation successful",
                            tvaultconf.PASS)
            else:
                reporting.add_test_step("Snapshot creation failed",
                            tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            #Enable back wlm-workloads service on specific host on which
            #snapshot was running
            if self.update_wlm_service(snapshot_data['host'], 'enable'):
                reporting.add_test_step("Enable wlm service on snapshot host",
                        tvaultconf.PASS)
            else:
                reporting.add_test_step("Enable wlm service on snapshot host",
                        tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_8_wlm_service(self):
        try:
            reporting.add_test_script(str(__name__) + \
                    "_disable_wlm_workloads_check_snapshot_request")
            node_names = []
            vm_list = []
            wids = []
            snapshots = []

            wlm_nodes = self.get_wlm_nodes()
            node_names = [x['node'] for x in wlm_nodes]
            for i in range(2):
                vm_id = self.create_vm()
                vm_list.append(vm_id)

            for i in range(2):
                try:
                    wid = self.workload_create([vm_list[i]])
                    LOG.debug(f"Workload ID-{i+1}: {wid}")
                    wids.append(wid)
                except Exception as e:
                    raise Exception(e)
                if wid:
                    self.wait_for_workload_tobe_available(wid)
                    workload_status = self.getWorkloadStatus(wid)
                    if(workload_status == "available"):
                        reporting.add_test_step(f"Create workload-{i+1}",
                                tvaultconf.PASS)
                    else:
                        raise Exception(f"Create workload-{i+1}")
                else:
                    raise Exception(f"Create workload-{i+1}")

            #Disable wlm-workloads on remaining nodes and enable only on 1 node
            for i in range(0, len(node_names)-1):
                if self.update_wlm_service(node_names[i], 'disable'):
                    reporting.add_test_step(f"Disable wlm service on host {node_names[i]}",
                        tvaultconf.PASS)
                else:
                    reporting.add_test_step(f"Disable wlm service on host {node_names[i]}",
                        tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            wlm_nodes = self.get_wlm_nodes()

            #Trigger snapshots for both workloads
            for i in range(len(wids)):
                snapshot_id = self.workload_snapshot(wids[i], True)
                snapshots.append(snapshot_id)
                if snapshot_id:
                    reporting.add_test_step(f"Trigger snapshot-{i+1}",
                            tvaultconf.PASS)
                else:
                    raise Exception(f"Trigger snapshot-{i+1}")
                snapshot_data = self.getSnapshotDetails(wids[i], snapshot_id)
                if snapshot_data['host'] != node_names[-1]:
                    reporting.add_test_step(f"Snapshot-{i+1} scheduled on " +\
                            f"disabled host {snapshot_data['host']}",
                            tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
                else:
                    reporting.add_test_step(f"Snapshot-{i+1} scheduled on " +\
                            f"host {snapshot_data['host']}", tvaultconf.PASS)
            for wid in wids:
                self.wait_for_workload_tobe_available(wid)

            #Enable wlm-workloads on disabled nodes
            for i in range(0, len(node_names)-1):
                if self.update_wlm_service(node_names[i], 'enable'):
                    reporting.add_test_step(f"Enable wlm service on host {node_names[i]}",
                        tvaultconf.PASS)
                else:
                    reporting.add_test_step(f"Enable wlm service on host {node_names[i]}",
                        tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
            wlm_nodes = self.get_wlm_nodes()

            #Trigger snapshots for both workloads
            for i in range(len(wids)):
                snapshot_id = self.workload_snapshot(wids[i], True)
                snapshots.append(snapshot_id)
                if snapshot_id:
                    reporting.add_test_step(f"Trigger snapshot-{i+1}",
                            tvaultconf.PASS)
                else:
                    raise Exception(f"Trigger snapshot-{i+1}")
                snapshot_data = self.getSnapshotDetails(wids[i], snapshot_id)
                reporting.add_test_step(f"Snapshot-{i+1} scheduled on host "+\
                        f"{snapshot_data['host']}", tvaultconf.PASS)
            for wid in wids:
                self.wait_for_workload_tobe_available(wid)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            #Enable back wlm-workloads service on all nodes
            for node in node_names:
                self.update_wlm_service(node, 'enable')
            wlm_nodes = self.get_wlm_nodes()
            reporting.test_case_to_write()

<<<<<<< HEAD
=======
    @decorators.attr(type='workloadmgr_cli')
    def test_9_wlm_service(self):
        try:
            reporting.add_test_script(str(__name__) + \
                    "_disable_service_snapshot_reset")
            node_names = []
            vm_id = self.create_vm()
            wlm_nodes = self.get_wlm_nodes()

            try:
                wid = self.workload_create([vm_id])
                LOG.debug("Workload ID: " + str(wid))
            except Exception as e:
                raise Exception(e)
            if wid:
                self.wait_for_workload_tobe_available(wid)
                workload_status = self.getWorkloadStatus(wid)
                if(workload_status == "available"):
                    reporting.add_test_step("Create workload", tvaultconf.PASS)
                else:
                    raise Exception("Create workload")
            else:
                raise Exception("Create workload")

            #Trigger snapshot
            snapshot_id = self.workload_snapshot(wid, True)
            if snapshot_id:
                reporting.add_test_step("Trigger snapshot", tvaultconf.PASS)
            else:
                raise Exception("Trigger snapshot")
            time.sleep(20)
            snapshot_data = self.getSnapshotDetails(wid, snapshot_id)

            #Disable wlm-workloads service on specific host on which
            #snapshot is running
            if self.update_wlm_service(snapshot_data['host'], 'disable'):
                reporting.add_test_step("Disable wlm service on snapshot host",
                        tvaultconf.PASS)
            else:
                reporting.add_test_step("Disable wlm service on snapshot host",
                        tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            snapshot_reset = command_argument_string.snapshot_reset + snapshot_id
            error = cli_parser.cli_error(snapshot_reset)
            LOG.debug(f"Error returned from CLI: {error}")
            err_msg = tvaultconf.snapshot_reset_err_msg + \
                    snapshot_data['host'] + ")"
            if error and \
                    (str(error.strip('\n')).find(err_msg) != -1):
                reporting.add_test_step("Snapshot-reset returned proper error message",
                        tvaultconf.PASS)
            else:
                reporting.add_test_step("Snapshot-reset did not return proper message",
                        tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            self.wait_for_workload_tobe_available(wid)
            snapshot_status = self.getSnapshotStatus(wid, snapshot_id)
            if snapshot_status == 'available':
                reporting.add_test_step("Snapshot creation successful",
                            tvaultconf.PASS)
            else:
                reporting.add_test_step("Snapshot creation failed",
                            tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            #Enable back wlm-workloads service on specific host on which
            #snapshot was running
            if self.update_wlm_service(snapshot_data['host'], 'enable'):
                reporting.add_test_step("Enable wlm service on snapshot host",
                        tvaultconf.PASS)
            else:
                reporting.add_test_step("Enable wlm service on snapshot host",
                        tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

>>>>>>> upstream/stable/5.0
