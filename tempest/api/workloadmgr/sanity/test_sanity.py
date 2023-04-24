from tempest.api.workloadmgr import base
from tempest import config
from tempest.lib import decorators
import time
from oslo_log import log as logging
from tempest.common import waiters
from tempest import tvaultconf
from tempest import reporting
from tempest.lib.services.compute import base_compute_client as api_version

LOG = logging.getLogger(__name__)
CONF = config.CONF

class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()

    def _attached_volume_prerequisite(self, volume_type_id):
        try:
            self.volume_id = self.create_volume(
                    volume_type_id=volume_type_id)
            self.vm_id = self.create_vm()
            self.attach_volume(self.volume_id, self.vm_id,
                               device=tvaultconf.volumes_parts[0])
            return True
        except Exception as e:
            LOG.error("Exception in _attached_volume_prerequisite : %s",str(e))
            return False

    def _boot_from_volume_prerequisite(self, volume_type_id):
        try:
            self.volume_id = self.create_volume(
                    size=tvaultconf.bootfromvol_vol_size,
                    image_id=CONF.compute.image_ref,
                    volume_type_id=volume_type_id)
            self.set_volume_as_bootable(self.volume_id)
            self.block_mapping_details = [{"source_type": "volume",
                                           "delete_on_termination": "false",
                                           "boot_index": 0,
                                           "uuid": self.volume_id,
                                           "destination_type": "volume"}]
            self.vm_id = self.create_vm(
                image_id="", block_mapping_data=self.block_mapping_details)
            return True
        except Exception as e:
            LOG.error(
                "Exception in _boot_from_volume_prerequisite : " +
                str(e))
            return False

    def _create_workload(self, workload_instances, encrypt=False, secret=""):
        time.sleep(5)
        self.workload_id = self.workload_create(
            workload_instances, encryption=encrypt,
            secret_uuid=secret, workload_cleanup=False)
        self.wait_for_workload_tobe_available(self.workload_id)
        self.workload_status = self.getWorkloadStatus(self.workload_id)
        self.workload_details = self.getWorkloadDetails(self.workload_id)

    def _create_snapshot(self, workload_id, snapshot_type):
        time.sleep(5)
        if snapshot_type.lower() == 'full':
            is_full = True
        else:
            is_full = False
        self.snapshot_id = self.workload_snapshot(
            workload_id, is_full, snapshot_cleanup=False)
        self.snapshot_status = self.getSnapshotStatus(
            workload_id, self.snapshot_id)

    def _wait_for_workload(self, workload_id, snapshot_id):
        self.wait_for_workload_tobe_available(workload_id)
        return self.getSnapshotStatus(workload_id, snapshot_id)

    def _trigger_selective_restore(
        self,
        workload_instances,
        workload_id,
        snapshot_id):
        self.instance_details = []
        int_net_1_name = self.get_net_name(CONF.network.internal_network_id)
        LOG.debug("int_net_1_name" + str(int_net_1_name))
        int_net_1_subnets = self.get_subnet_id(
            CONF.network.internal_network_id)
        LOG.debug("int_net_1_subnet" + str(int_net_1_subnets))

        # Create instance details for restore.json
        for i in range(len(workload_instances)):
            vm_name = str(workload_instances[i]) + "_restored"
            temp_instance_data = {'id': workload_instances[i],
                                  'include': True,
                                  'restore_boot_disk': True,
                                  'name': vm_name,
                                  'vdisks': []
                                  }
            self.instance_details.append(temp_instance_data)
        LOG.debug("Instance details for restore: " +
                  str(self.instance_details))

        # Create network details for restore.json
        snapshot_network = {'name': int_net_1_name,
                            'id': CONF.network.internal_network_id,
                            'subnet': {'id': int_net_1_subnets}
                            }
        target_network = {'name': int_net_1_name,
                          'id': CONF.network.internal_network_id,
                          'subnet': {'id': int_net_1_subnets}
                          }
        self.network_details = [{'snapshot_network': snapshot_network,
                                 'target_network': target_network}]
        LOG.debug("Network details for restore: " + str(self.network_details))

        # Trigger selective restore
        time.sleep(15)
        self.restore_id = self.snapshot_selective_restore(
            workload_id,
            snapshot_id,
            restore_name=tvaultconf.restore_name,
            instance_details=self.instance_details,
            network_details=self.network_details,
            restore_cleanup=False)
        return self.restore_id

    def _delete_restore(self, workload_id, snapshot_id, restore_id):
        return self.restore_delete(workload_id, snapshot_id, restore_id)

    def _delete_restored_vms(self, restore_id):
        restored_vms = self.get_restored_vm_list(restore_id)
        restored_volumes = self.get_restored_volume_list(restore_id)
        self.delete_restored_vms(restored_vms, restored_volumes)

    def _delete_snapshot(self, workload_id, snapshot_id):
        return self.snapshot_delete(workload_id, snapshot_id)

    def _delete_workload(self, workload_id):
        return self.workload_delete(workload_id)

    @decorators.attr(type='workloadmgr_api')
    def test_sanity(self):
        try:
            result_json = {}
            for test in tvaultconf.enabled_tests:
                result_json[test] = {}
            LOG.debug("Result json: " + str(result_json))

            for k in result_json.keys():
                result_json[k]['result'] = {}
                vol = k.split('_')[-1]
                vol_type_id = CONF.volume.volume_types[vol]
                if (vol.lower().find("multiattach") != -1):
                    api_version.COMPUTE_MICROVERSION = '2.60'
                if(k.lower().find("attach") != -1):
                    if self._attached_volume_prerequisite(vol_type_id):
                        result_json[k]['Prerequisite'] = tvaultconf.PASS
                    else:
                        result_json[k]['Prerequisite'] = tvaultconf.FAIL
                elif(k.lower().find("boot") != -1):
                    if self._boot_from_volume_prerequisite(vol_type_id):
                        result_json[k]['Prerequisite'] = tvaultconf.PASS
                    else:
                        result_json[k]['Prerequisite'] = tvaultconf.FAIL
                if (vol.lower().find("multiattach") != -1):
                    api_version.COMPUTE_MICROVERSION = None
                if(result_json[k]['Prerequisite'] == tvaultconf.PASS):
                    result_json[k]['instances'] = self.vm_id
                    result_json[k]['volumes'] = self.volume_id
                    self.vol_encrypt = self.get_volume_encryption_status(self.volume_id)
                    result_json[k]['encryption'] = self.vol_encrypt
                    if self.vol_encrypt:
                        self.secret_uuid = self.create_secret()
                        result_json[k]['secret_uuid'] = self.secret_uuid
                    else:
                        self.secret_uuid = ""
                    self.workload_id = None
                    try:
                        self._create_workload([self.vm_id], self.vol_encrypt, self.secret_uuid)
                        result_json[k]['workload'] = self.workload_id
                        result_json[k]['workload_status'] = self.workload_status
                        if(self.workload_status == "available"):
                            result_json[k]['result']['Create_Workload'] = \
                                tvaultconf.PASS
                        elif(self.workload_status == "error"):
                            result_json[k]['workload_error_msg'] = \
                                    self.workload_details['error_msg']
                            result_json[k]['result']['Create_Workload'] = \
                                tvaultconf.FAIL + "\nERROR " + \
                                result_json[k]['workload_error_msg']

                    except Exception as e:
                        result_json[k]['workload_error_msg'] = str(e)
                        result_json[k]['result']['Create_Workload'] = \
                                tvaultconf.FAIL + "\nERROR " + \
                                result_json[k]['workload_error_msg']
                        continue

                    if self.workload_id and \
                        self.workload_status == "available":
                        try:
                            self._create_snapshot(self.workload_id, 'full')
                            result_json[k]['snapshot'] = self.snapshot_id
                            result_json[k]['snapshot_status'] = self.snapshot_status
                        except Exception as e:
                            result_json[k]['snapshot_error_msg'] = str(e)
                            result_json[k]['result']['Create_Full_Snapshot'] = \
                                tvaultconf.FAIL + "\nERROR " + \
                                result_json[k]['snapshot_error_msg']
                            continue
                else:
                    result_json[k]['result']['Prerequisite'] = tvaultconf.FAIL
                    continue
            LOG.debug("Result json after trigger full snapshot: " +\
                      str(result_json))

            for k in result_json.keys():
                if('snapshot_status' in result_json[k].keys()):
                    result_json[k]['snapshot_status'] = self._wait_for_workload(
                        result_json[k]['workload'], result_json[k]['snapshot'])
                    result_json[k]['workload_status'] = self.getWorkloadStatus(
                        result_json[k]['workload'])
                    result_json[k]['snapshot_size'] = (
                        self.getSnapshotDetails(
                            result_json[k]['workload'],
                            result_json[k]['snapshot']))['size']
                    result_json[k]['snapshot_restore_size'] = \
                        (self.getSnapshotDetails(result_json[k]['workload'],
                            result_json[k]['snapshot']))['restore_size']
                    result_json[k]['snapshot_time_taken'] = (
                        self.getSnapshotDetails(
                            result_json[k]['workload'],
                            result_json[k]['snapshot']))['time_taken']
                    result_json[k]['snapshot_uploaded_size'] = \
                        (self.getSnapshotDetails(result_json[k]['workload'],
                            result_json[k]['snapshot']))['uploaded_size']
                    if(result_json[k]['snapshot_status'] == "available"):
                        result_json[k]['result']['Create_Full_Snapshot'] = \
                            tvaultconf.PASS
                    else:
                        result_json[k]['snapshot_error_msg'] = (
                            self.getSnapshotDetails(result_json[k]['workload'],
                                result_json[k]['snapshot']))['error_msg']
                        result_json[k]['result']['Create_Full_Snapshot'] = \
                            tvaultconf.FAIL + \
                            "\nERROR " + result_json[k]['snapshot_error_msg']
            LOG.debug("Result json after full snapshot complete: " +\
                      str(result_json))

            for k in result_json.keys():
                if(result_json[k]['result']['Create_Full_Snapshot'] == 
                        tvaultconf.PASS):
                    self._create_snapshot(result_json[k]['workload'], 'incremental')
                    result_json[k]['incr_snapshot'] = self.snapshot_id
                    result_json[k]['incr_snapshot_status'] = self.snapshot_status
            LOG.debug("Result json after trigger incremental snapshot: " +\
                      str(result_json))

            for k in result_json.keys():
                if('incr_snapshot_status' in result_json[k].keys()):
                    result_json[k]['incr_snapshot_status'] = self._wait_for_workload(
                        result_json[k]['workload'], result_json[k]['incr_snapshot'])
                    result_json[k]['workload_status'] = self.getWorkloadStatus(
                        result_json[k]['workload'])
                    result_json[k]['incr_snapshot_size'] = (
                        self.getSnapshotDetails(
                            result_json[k]['workload'],
                            result_json[k]['incr_snapshot']))['size']
                    result_json[k]['incr_snapshot_restore_size'] = \
                        (self.getSnapshotDetails(result_json[k]['workload'],
                            result_json[k]['incr_snapshot']))['restore_size']
                    result_json[k]['incr_snapshot_time_taken'] = (
                        self.getSnapshotDetails(
                            result_json[k]['workload'],
                            result_json[k]['incr_snapshot']))['time_taken']
                    result_json[k]['incr_snapshot_uploaded_size'] = \
                        (self.getSnapshotDetails(result_json[k]['workload'],
                            result_json[k]['incr_snapshot']))['uploaded_size']
                    if(result_json[k]['incr_snapshot_status'] == "available"):
                        result_json[k]['result']['Create_Incremental_Snapshot'] = \
                            tvaultconf.PASS
                    else:
                        result_json[k]['incr_snapshot_error_msg'] = (
                            self.getSnapshotDetails(result_json[k]['workload'],
                                result_json[k]['incr_snapshot']))['error_msg']
                        result_json[k]['result']['Create_Incremental_Snapshot'] = \
                            tvaultconf.FAIL + \
                            "\nERROR " + result_json[k]['incr_snapshot_error_msg']
            LOG.debug("Result json after incremental snapshot complete: " +\
                      str(result_json))

            self.restore_id = None
            for k in result_json.keys():
                if('incr_snapshot_status' in result_json[k].keys() and \
                        result_json[k]['incr_snapshot_status'] == "available"):
                    try:
                        self.restore_id = self._trigger_selective_restore(
                            [result_json[k]['instances']],
                            result_json[k]['workload'],
                            result_json[k]['incr_snapshot'])
                        result_json[k]['restore'] = self.restore_id
                    except Exception as e:
                        error_message = str(e).replace("<br /><br />\n\n\n","")
                        result_json[k]['restore_error_msg'] = error_message
                        result_json[k]['result']['Selective_Restore'] = \
                            tvaultconf.FAIL + "\nERROR " + \
                            result_json[k]['restore_error_msg']
                        continue
            LOG.debug("Result json after trigger selective restore: " +
                        str(result_json))

            if self.restore_id:
                for k in result_json.keys():
                    if('restore' in result_json[k].keys()):
                        result_json[k]['incr_snapshot_status'] = self._wait_for_workload(
                            result_json[k]['workload'],
                            result_json[k]['incr_snapshot'])
                        result_json[k]['workload_status'] = self.getWorkloadStatus(
                            result_json[k]['workload'])
                        result_json[k]['restore_status'] = self.getRestoreStatus(
                            result_json[k]['workload'], result_json[k]['incr_snapshot'],
                            result_json[k]['restore'])
                        result_json[k]['restore_size'] = (
                            self.getRestoreDetails(
                                result_json[k]['restore']))['size']
                        result_json[k]['restore_time_taken'] = (
                            self.getRestoreDetails(result_json[k]['restore']))\
                                    ['time_taken']
                        result_json[k]['restore_uploaded_size'] = (
                            self.getRestoreDetails(result_json[k]['restore']))\
                                    ['uploaded_size']
                        if(result_json[k]['restore_status'] == "available"):
                            result_json[k]['result']['Selective_Restore'] = \
                                tvaultconf.PASS
                        else:
                            result_json[k]['restore_error_msg'] = (
                                self.getRestoreDetails(result_json[k]['restore']))\
                                        ['error_msg']
                            result_json[k]['restore_error_msg'] = (result_json[k]['restore_error_msg']).replace("<br /><br />\n\n\n", "")
                            result_json[k]['result']['Selective_Restore'] = \
                                tvaultconf.FAIL + "\nERROR " + \
                                result_json[k]['restore_error_msg']
                LOG.debug(
                    "Result json after selective restore complete: " +
                    str(result_json))

                for k in result_json.keys():
                    if('restore_status' in result_json[k].keys()):
                        result_json[k]['incr_snapshot_status'] = self._wait_for_workload(
                            result_json[k]['workload'], result_json[k]['incr_snapshot'])
                        result_json[k]['workload_status'] = self.getWorkloadStatus(
                            result_json[k]['workload'])
                        result_json[k]['restore_status'] = self.getRestoreStatus(
                            result_json[k]['workload'], result_json[k]['incr_snapshot'],
                            result_json[k]['restore'])
                        if(result_json[k]['workload_status'] == "available" and \
                                result_json[k]['restore_status'] in \
                                    ("available", "error")):
                            self._delete_restored_vms(result_json[k]['restore'])
                            result_json[k]['restore_delete_response'] = \
                                self._delete_restore(result_json[k]['workload'],
                                        result_json[k]['incr_snapshot'],
                                        result_json[k]['restore'])
                            # if(result_json[k]['restore_delete_response']):
                            #    result_json[k]['result']['Delete_Restore'] = tvaultconf.PASS
                            # else:
                            #    result_json[k]['result']['Delete_Restore'] = tvaultconf.FAIL
                LOG.debug("Result json after delete restore: " + str(result_json))

            for k in result_json.keys():
                if('snapshot_status' in result_json[k].keys()):
                    result_json[k]['snapshot_status'] = self._wait_for_workload(
                        result_json[k]['workload'], result_json[k]['snapshot'])
                    result_json[k]['workload_status'] = self.getWorkloadStatus(
                        result_json[k]['workload'])
                    if(result_json[k]['workload_status'] == "available" and \
                            result_json[k]['snapshot_status'] in \
                                ("available", "error")):
                        result_json[k]['snapshot_delete_response'] = \
                            self._delete_snapshot(result_json[k]['workload'],
                                    result_json[k]['snapshot'])
            LOG.debug("Result json after delete snapshot: " + str(result_json))

            for k in result_json.keys():
                if('workload_status' in result_json[k].keys()):
                    result_json[k]['workload_status'] = self.getWorkloadStatus(
                        result_json[k]['workload'])
                    if(result_json[k]['workload_status'] in \
                            ("available", "error")):
                        result_json[k]['workload_delete_response'] = \
                            self._delete_workload(result_json[k]['workload'])
                        # if(result_json[k]['workload_delete_response']):
                        #    result_json[k]['result']['Delete_Workload'] = tvaultconf.PASS
                        # else:
                        #    result_json[k]['result']['Delete_Workload'] = tvaultconf.FAIL
            LOG.debug("Result json after delete workload: " + str(result_json))

        except Exception as e:
            LOG.error("Exception: " + str(e))

        finally:
            # Add results to sanity report
            result_json2={}
            for k in result_json.keys():
                if 'encryption' in result_json[k].keys():
                    if result_json[k]['encryption']:
                        result_json2[k+'_encrypted']=result_json[k]
                    else:
                        result_json2[k+'_unencrypted']=result_json[k]
                else:
                    result_json2[k]=result_json[k]

            LOG.debug("Finally Result json: " + str(result_json2))
            reporting.add_result_json(result_json2)
            for k, v in result_json2.items():
                if(('result' in v.keys()) and (len(v['result'].keys()) > 0)):
                    for k1 in list(v['result'].keys()):
                        reporting.add_sanity_results(
                            k1 + "_" + k, v['result'][k1])

            for k, v in result_json2.items():
                for k1, v1 in v.items():
                    if('size' in k1 or 'time' in k1):
                        reporting.add_sanity_stats(k, k1, v1)

