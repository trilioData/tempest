import os
import sys

from oslo_log import log as logging

from tempest import command_argument_string
from tempest import config
from tempest import reporting
from tempest import tvaultconf
from tempest.api.workloadmgr import base
from tempest.lib import decorators
from tempest.util import cli_parser

sys.path.append(os.getcwd())

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    @decorators.attr(type='workloadmgr_cli')
    def test_01_expired_license(self):
        reporting.add_test_script(str(__name__) + "_expired_license")
        try:
            # Create license using CLI command
            self.cmd = command_argument_string.license_create + \
                tvaultconf.expired_license_filename
            LOG.debug("License create command: " + str(self.cmd))
            rc = cli_parser.cli_returncode(self.cmd)
            LOG.debug("rc value: " + str(rc))
            if rc != 0:
                reporting.add_test_step(
                    "Execute license_create command with expired license",
                    tvaultconf.FAIL)
                raise Exception("Command not executed correctly")
            else:
                reporting.add_test_step(
                    "Execute license_create command with expired license",
                    tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            out = self.get_license_check()
            LOG.debug("license-check API output: " + str(out))
            if(str(out).find('License expired') != -1):
                reporting.add_test_step(
                    "Verify license expiration message", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify license expiration message", tvaultconf.FAIL)
                raise Exception(
                    "Incorrect license expiration message displayed")
            reporting.test_case_to_write()
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    @decorators.attr(type='workloadmgr_cli')
    def test_02_invalid_license(self):
        reporting.add_test_script(str(__name__) + "_invalid_license")
        try:
            # Create license using CLI command
            self.cmd = command_argument_string.license_create + \
                tvaultconf.invalid_license_filename
            LOG.debug("License create command: " + str(self.cmd))
            rc = cli_parser.cli_returncode(self.cmd)
            if rc == 0:
                reporting.add_test_step(
                    "Execute license_create command with invalid license",
                    tvaultconf.PASS)
                LOG.debug("Command executed correctly")
            else:
                reporting.add_test_step(
                    "Execute license_create command with invalid license",
                    tvaultconf.FAIL)
                raise Exception("Command not executed correctly")

            self.license_txt = ""
            # Get license key content
            with open(tvaultconf.invalid_license_filename) as f:
                for line in f:
                    self.license_txt += line
            LOG.debug("License text: " + str(self.license_txt))
            out = self.create_license(
                tvaultconf.invalid_license_filename, self.license_txt)
            LOG.debug("license-create API output: " + str(out))
            if(str(out).find('Cannot verify the license signature') != -1):
                reporting.add_test_step(
                    "Verify error message", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "Verify error message", tvaultconf.FAIL)
                raise Exception("Incorrect error message displayed")
            reporting.test_case_to_write()
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    @decorators.attr(type='workloadmgr_cli')
    def test_03_license_check_vms(self):
        reporting.add_test_script(str(__name__) + "_check_vms")
        try:
            # Create license using CLI command
            self.cmd = command_argument_string.license_create + tvaultconf.vm_license_filename
            rc = cli_parser.cli_returncode(self.cmd)
            if rc != 0:
                reporting.add_test_step("Apply 10VM license", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step("Apply 10VM license", tvaultconf.PASS)

            # Create simple workload
            self.workload_instances = []
            for i in range(0, 2):
                self.vm_id = self.create_vm()
                self.volume_id = self.create_volume()
                self.attach_volume(self.volume_id, self.vm_id)
                self.workload_instances.append(self.vm_id)
            self.wid = self.workload_create(
                self.workload_instances, tvaultconf.parallel)
            LOG.debug("Workload ID: " + str(self.wid))

            # Verify license-check CLI command
            self.cmd = command_argument_string.license_check
            rc = cli_parser.cli_returncode(self.cmd)
            if rc != 0:
                reporting.add_test_step(
                    "Execute license-check command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute license-check command", tvaultconf.PASS)

            # Verification
            out = cli_parser.cli_output(self.cmd)
            LOG.debug("CLI Response: " + str(out))
            if(str(out).find('2') != -1):
                reporting.add_test_step(
                    "License-check verification", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "License-check verification", tvaultconf.FAIL)
                raise Exception("License-check verification failed")
            reporting.test_case_to_write()
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    @decorators.attr(type='workloadmgr_cli')
    def license_check_capacity(self):
        reporting.add_test_script(str(__name__) + "_check_capacity")
        try:
            # Create license using CLI command
            self.cmd = command_argument_string.license_create + \
                tvaultconf.capacity_license_filename
            rc = cli_parser.cli_returncode(self.cmd)
            if rc != 0:
                reporting.add_test_step("Apply 100GB license", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step("Apply 100GB license", tvaultconf.PASS)

            # Verify license-check CLI command
            self.cmd = command_argument_string.license_check
            rc = cli_parser.cli_returncode(self.cmd)
            if rc != 0:
                reporting.add_test_step(
                    "Execute license-check command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute license-check command", tvaultconf.PASS)

            # Verification
            out = cli_parser.cli_output(self.cmd)
            LOG.debug("CLI Response: " + str(out))
            get_usage_tvault = "df -h | grep triliovault-mounts"
            ssh = self.SshRemoteMachineConnection(
                tvaultconf.tvault_ip[0],
                tvaultconf.tvault_dbusername,
                tvaultconf.tvault_password)
            stdin, stdout, stderr = ssh.exec_command(get_usage_tvault)
            tmp = ' '.join(stdout.read().split())
            usage = tmp.split(' ')
            LOG.debug("Data from Tvault: " + str(usage) +
                      " Usage: " + str(usage[2]))
            ssh.close()
            if(str(out).find(usage[2]) != -1):
                reporting.add_test_step(
                    "License-check verification", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "License-check verification", tvaultconf.FAIL)
                raise Exception("License-check verification failed")
            reporting.test_case_to_write()
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    @decorators.attr(type='workloadmgr_cli')
    def test_05_license_check_compute(self):
        reporting.add_test_script(str(__name__) + "_check_compute")
        try:
            # Create license using CLI command
            self.cmd = command_argument_string.license_create + \
                tvaultconf.compute_license_filename
            rc = cli_parser.cli_returncode(self.cmd)
            if rc != 0:
                reporting.add_test_step(
                    "Apply 10 compute node license", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Apply 10 compute node license", tvaultconf.PASS)

            # Verify license-check CLI command
            self.cmd = command_argument_string.license_check
            rc = cli_parser.cli_returncode(self.cmd)
            if rc != 0:
                reporting.add_test_step(
                    "Execute license-check command", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step(
                    "Execute license-check command", tvaultconf.PASS)

            # Verification
            out = cli_parser.cli_output(self.cmd)
            LOG.debug("CLI Response: " + str(out))
            if(str(out).find('Number of compute nodes deployed \'' + str(tvaultconf.no_of_compute_nodes) + '\'') != -1):
                reporting.add_test_step(
                    "License-check verification", tvaultconf.PASS)
            else:
                reporting.add_test_step(
                    "License-check verification", tvaultconf.FAIL)
                raise Exception("License-check verification failed")
            reporting.test_case_to_write()
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
