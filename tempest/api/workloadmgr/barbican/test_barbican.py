from tempest.api.workloadmgr import base
from tempest import config
from tempest.lib import decorators
import time
from oslo_log import log as logging
from tempest import tvaultconf
from tempest import reporting
from tempest import command_argument_string
from tempest.util import cli_parser
from tempest.util import query_data

LOG = logging.getLogger(__name__)
CONF = config.CONF

class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()

    @decorators.attr(type='workloadmgr_api')
    def test_1_barbican(self):
        reporting.add_test_script(str(__name__) + "_create_encrypted_workload_api")
        try:
            for vol_type, vol_typeid in CONF.volume.volume_types.items():
                self.vm_id = self.create_vm()
                self.volume_id = self.create_volume(volume_type_id=vol_typeid)
                self.attach_volume(self.volume_id, self.vm_id)
                self.secret_uuid = self.create_secret()

                # Create workload with API
                self.wid = self.workload_create([self.vm_id], tvaultconf.workload_type_id,
                        encryption=True, secret_uuid=self.secret_uuid)
                LOG.debug("Workload ID: " + str(self.wid))
                if(self.wid is not None):
                    self.wait_for_workload_tobe_available(self.wid)
                    if(self.getWorkloadStatus(self.wid) == "available"):
                        reporting.add_test_step(f"Create encrypted workload with attach {vol_type} volume", tvaultconf.PASS)
                    else:
                        reporting.add_test_step(f"Create encrypted workload with attach {vol_type} volume", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)
                else:
                    reporting.add_test_step("Create encrypted workload with attach {vol_type} volume", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)

            for vol_type, vol_typeid in CONF.volume.volume_types.items():
                self.volume_id = self.create_volume(volume_type_id=vol_typeid,
                        size=tvaultconf.bootfromvol_vol_size,
                        image_id=CONF.compute.image_ref)
                self.set_volume_as_bootable(self.volume_id)
                self.block_mapping_details = [{"source_type": "volume",
                                               "delete_on_termination": "false",
                                               "boot_index": 0,
                                               "uuid": self.volume_id,
                                               "destination_type": "volume"}]
                self.vm_id = self.create_vm(image_id="",
                        block_mapping_data=self.block_mapping_details)
                self.secret_uuid = self.create_secret()

                # Create workload with API
                self.wid = self.workload_create([self.vm_id], tvaultconf.workload_type_id,
                        encryption=True, secret_uuid=self.secret_uuid)
                LOG.debug("Workload ID: " + str(self.wid))
                if(self.wid is not None):
                    self.wait_for_workload_tobe_available(self.wid)
                    if(self.getWorkloadStatus(self.wid) == "available"):
                        reporting.add_test_step(f"Create encrypted workload with {vol_type} boot volume", tvaultconf.PASS)
                    else:
                        reporting.add_test_step(f"Create encrypted workload with {vol_type} boot volume", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)
                else:
                    reporting.add_test_step("Create encrypted workload with {vol_type} boot volume", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_cli')
    def test_2_barbican(self):
        reporting.add_test_script(str(__name__) + "_create_encrypted_workload_cli")
        try:
            for vol_type, vol_typeid in CONF.volume.volume_types.items():
                self.vm_id = self.create_vm()
                self.volume_id = self.create_volume(volume_type_id=vol_typeid)
                self.attach_volume(self.volume_id, self.vm_id)
                self.secret_uuid = self.create_secret()

                # Create workload with CLI command
                workload_create = command_argument_string.workload_create + \
                    " --instance instance-id=" + str(self.vm_id) + \
                    " --encryption=true --secret-uuid=" + str(self.secret_uuid)
                rc = cli_parser.cli_returncode(workload_create)
                if rc != 0:
                    reporting.add_test_step(
                        f"Execute workload-create command for {vol_type} volume attached vm",
                        tvaultconf.FAIL)
                    raise Exception("Command did not execute correctly")
                else:
                    reporting.add_test_step(
                        f"Execute workload-create command for {vol_type} volume attached vm",
                        tvaultconf.PASS)
                LOG.debug("Command executed correctly")

                time.sleep(10)
                self.wid = query_data.get_workload_id(tvaultconf.workload_name)
                LOG.debug("Workload ID: " + str(self.wid))
                if(self.wid is not None):
                    self.wait_for_workload_tobe_available(self.wid)
                    if(self.getWorkloadStatus(self.wid) == "available"):
                        reporting.add_test_step(f"Create encrypted workload with attach {vol_type} volume", tvaultconf.PASS)
                    else:
                        reporting.add_test_step(f"Create encrypted workload with attach {vol_type} volume", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)
                else:
                    reporting.add_test_step("Create encrypted workload with attach {vol_type} volume", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)

            for vol_type, vol_typeid in CONF.volume.volume_types.items():
                self.volume_id = self.create_volume(volume_type_id=vol_typeid,
                        size=tvaultconf.bootfromvol_vol_size,
                        image_id=CONF.compute.image_ref)
                self.set_volume_as_bootable(self.volume_id)
                self.block_mapping_details = [{"source_type": "volume",
                                               "delete_on_termination": "false",
                                               "boot_index": 0,
                                               "uuid": self.volume_id,
                                               "destination_type": "volume"}]
                self.vm_id = self.create_vm(image_id="",
                        block_mapping_data=self.block_mapping_details)
                self.secret_uuid = self.create_secret()

                # Create workload with CLI command
                workload_create = command_argument_string.workload_create + \
                    " --instance instance-id=" + str(self.vm_id) + \
                    " --encryption=true --secret-uuid=" + str(self.secret_uuid)
                rc = cli_parser.cli_returncode(workload_create)
                if rc != 0:
                    reporting.add_test_step(
                        f"Execute workload-create command for {vol_type} boot volume vm",
                        tvaultconf.FAIL)
                    raise Exception("Command did not execute correctly")
                else:
                    reporting.add_test_step(
                        f"Execute workload-create command for {vol_type} boot volume vm",
                        tvaultconf.PASS)
                LOG.debug("Command executed correctly")

                time.sleep(10)
                self.wid = query_data.get_workload_id(tvaultconf.workload_name)
                LOG.debug("Workload ID: " + str(self.wid))
                if(self.wid is not None):
                    self.wait_for_workload_tobe_available(self.wid)
                    if(self.getWorkloadStatus(self.wid) == "available"):
                        reporting.add_test_step(f"Create encrypted workload with {vol_type} boot volume", tvaultconf.PASS)
                    else:
                        reporting.add_test_step(f"Create encrypted workload with {vol_type} boot volume", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)
                else:
                    reporting.add_test_step("Create encrypted workload with {vol_type} boot volume", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

