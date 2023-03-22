import operator
import os
import re
import subprocess
import sys
import time
from urllib.parse import urlencode

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

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()
        reporting.add_test_script(str(__name__))

    @decorators.attr(type='workloadmgr_api')
    def test_1_email(self):
        reporting.add_test_script(str(__name__) + "_smtp_with_password")
        try:
            # Fetch existing settings
            existing_setting = self.get_settings_list()
            LOG.debug("Existing setting list: " + str(existing_setting))
            # Delete any existing settings
            flag = False
            if(existing_setting != {}):
                for k, v in existing_setting.items():
                    if (self.delete_setting(k) == False):
                        flag = True
            if flag:
                reporting.add_test_step(
                    "Delete existing setting", tvaultconf.FAIL)
            else:
                self.wlm_client.client.get(
                        "/workloads/email/test_email?" + urlencode(tvaultconf.setting_data))
                cmd = 'curl  -u ' + tvaultconf.setting_data["smtp_default_recipient"] + ':' + \
                        tvaultconf.smtp_password + ' --silent "https://mail.google.com/mail/feed/atom"'
                op = subprocess.check_output(cmd, shell=True)
                if len(re.findall('Testing email configuration',
                    op.decode().split('<entry>')[1])) == 1:
                    LOG.debug(f"Email testing done correctly and email is: {op}")
                    reporting.add_test_step("Test email", tvaultconf.PASS)
                else:
                    reporting.add_test_step("Test email", tvaultconf.FAIL)
                    raise Exception("Test email")

                # Update trilioVault email settings
                settings_resp = self.update_email_setings(
                    tvaultconf.setting_data)
                setting_data_from_resp = {}

                for i in range(0, len(settings_resp)):
                    setting_data_from_resp[settings_resp[i][
                        'name']] = settings_resp[i]['value']
                LOG.debug("Settings data from response: " +
                          str(setting_data_from_resp) +
                          " ; original setting data: " +
                          str(tvaultconf.setting_data))
                del setting_data_from_resp['smtp_server_password']
                del tvaultconf.setting_data['smtp_server_password']
                if(operator.eq(setting_data_from_resp, tvaultconf.setting_data)):
                    reporting.add_test_step(
                        "Update email settings", tvaultconf.PASS)

                    # Enable email notification for project
                    enable_email_resp = self.update_email_setings(
                        tvaultconf.enable_email_notification)[0]
                    params = tvaultconf.setting_data
                    params['smtp_server_password'] = tvaultconf.smtp_password
                    if((str(enable_email_resp['name']) == 'smtp_email_enable') \
                            and (str(enable_email_resp['value']) == '1')):
                        reporting.add_test_step(
                            "Enable email notification for project", tvaultconf.PASS)

                        #existing_setting = self.get_settings_list()
                        #LOG.debug("Existing setting list: " + str(existing_setting))

                        # Delete the existing settings
                        #for k, v in existing_setting.items():
                        #    self.delete_setting(k)
                    else:
                        reporting.add_test_step(
                            "Enable email notification for project", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)
                else:
                    reporting.add_test_step(
                        "Update email settings", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def t2_email(self):
        reporting.add_test_script(str(__name__) + "_smtp_without_password")
        try:
            # Fetch existing settings
            existing_setting = self.get_settings_list()
            LOG.debug("Existing setting list: " + str(existing_setting))
            # Delete any existing settings
            flag = False
            if(existing_setting != {}):
                for k, v in existing_setting.items():
                    if (self.delete_setting(k) == False):
                        flag = True
            if flag:
                reporting.add_test_step(
                    "Delete existing setting", tvaultconf.FAIL)
            else:
                try:
                    self.wlm_client.client.get(
                        "/workloads/email/test_email?" + urlencode(tvaultconf.setting_data_pwdless))
                    reporting.add_test_step("Test email", tvaultconf.PASS)
                except Exception as e:
                    reporting.add_test_step("Test email", tvaultconf.FAIL)
                    raise Exception("Test email")

                # Update trilioVault email settings
                settings_resp = self.update_email_setings(
                    tvaultconf.setting_data_pwdless)
                setting_data_from_resp = {}

                for i in range(0, len(settings_resp)):
                    setting_data_from_resp[settings_resp[i][
                        'name']] = settings_resp[i]['value']
                LOG.debug("Settings data from response: " +
                          str(setting_data_from_resp) +
                          " ; original setting data: " +
                          str(tvaultconf.setting_data_pwdless))
                if(operator.eq(setting_data_from_resp, tvaultconf.setting_data_pwdless)):
                    reporting.add_test_step(
                        "Update email settings", tvaultconf.PASS)

                    # Enable email notification for project
                    enable_email_resp = self.update_email_setings(
                        tvaultconf.enable_email_notification)[0]
                    if((str(enable_email_resp['name']) == 'smtp_email_enable')\
                            and (str(enable_email_resp['value']) == '1')):
                        reporting.add_test_step(
                            "Enable email notification for project", tvaultconf.PASS)
                        existing_setting = self.get_settings_list()
                        LOG.debug("Existing setting list: " + str(existing_setting))

                        # Delete the existing settings
                        for k, v in existing_setting.items():
                            self.delete_setting(k)
                    else:
                        reporting.add_test_step(
                            "Enable email notification for project", tvaultconf.FAIL)
                        reporting.set_test_script_status(tvaultconf.FAIL)
                else:
                    reporting.add_test_step(
                        "Update email settings", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

    @decorators.attr(type='workloadmgr_api')
    def test_3_email(self):
        reporting.add_test_script(str(__name__) + "_email_notification")
        try:
            # Fetch existing settings
            existing_setting = self.get_settings_list()
            LOG.debug("Existing setting list: " + str(existing_setting))
            # Delete any existing settings
            flag = False
            if(existing_setting != {}):
                for k, v in existing_setting.items():
                    if (self.delete_setting(k) == False):
                        flag = True
            if flag:
                raise Exception("Delete existing setting")

            # Update trilioVault email settings
            settings_resp = self.update_email_setings(tvaultconf.setting_data)

            # Enable email notification for project
            enable_email_resp = self.update_email_setings(
                        tvaultconf.enable_email_notification)[0]
            params = tvaultconf.setting_data
            params['smtp_server_password'] = tvaultconf.smtp_password
            if((str(enable_email_resp['name']) == 'smtp_email_enable') \
                    and (str(enable_email_resp['value']) == '1')):
                reporting.add_test_step(
                    "Enable email notification for project", tvaultconf.PASS)
            else:
                raise Exception("Enable email notification for project")

            #Create workload
            vm_id = self.create_vm(vm_cleanup=False)
            wid = self.workload_create([vm_id])
            LOG.debug(f"Workload ID: {wid}")
            if wid:
                self.wait_for_workload_tobe_available(wid)
                if(self.getWorkloadStatus(wid) == "available"):
                    reporting.add_test_step("Create workload", tvaultconf.PASS)
                else:
                    raise Exception("Create workload")
            else:
                raise Exception("Create workload")
            workload_name = self.get_workload_details(wid)['name']
            LOG.debug(f"Workload Name: {workload_name}")

            snapshot_id = self.workload_snapshot(wid, True)
            LOG.debug(f"Snapshot ID: {snapshot_id}")
            self.wait_for_workload_tobe_available(wid)
            snapshot_status = self.getSnapshotStatus(wid, snapshot_id)
            LOG.debug(f"Snapshot status: {snapshot_status}")
            if snapshot_status == 'available':
                reporting.add_test_step("Create full snapshot", tvaultconf.PASS)
            else:
                raise Exception("Create full snapshot")
            time.sleep(10)

            cmd = 'curl  -u ' + tvaultconf.setting_data[
                    "smtp_default_recipient"] + ':' + tvaultconf.smtp_password \
                    + ' --silent "https://mail.google.com/mail/feed/atom"'
            op = subprocess.check_output(cmd, shell=True)
            LOG.debug(f"Gmail output: {op}")

            if len(re.findall(f'{workload_name} Snapshot finished successfully',
                    op.decode().split('<entry>')[1])) == 1:
                LOG.debug("Snapshot success email sent to user")
                reporting.add_test_step("Snapshot success email sent to user", tvaultconf.PASS)
            else:
                LOG.error("Snapshot success email not sent to user")
                reporting.add_test_step("Snapshot success email sent to user", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            snapshot_id = self.workload_snapshot(wid, False)
            LOG.debug(f"Incremental Snapshot ID: {snapshot_id}")
            self.wait_for_workload_tobe_available(wid)
            snapshot_status = self.getSnapshotStatus(wid, snapshot_id)
            LOG.debug(f"Incremental Snapshot status: {snapshot_status}")
            if snapshot_status == 'available':
                reporting.add_test_step("Create incremental snapshot", tvaultconf.PASS)
            else:
                raise Exception("Create incremental snapshot")
            time.sleep(10)

            cmd = 'curl  -u ' + tvaultconf.setting_data[
                    "smtp_default_recipient"] + ':' + tvaultconf.smtp_password \
                    + ' --silent "https://mail.google.com/mail/feed/atom"'
            op = subprocess.check_output(cmd, shell=True)
            LOG.debug(f"Gmail output: {op}")

            if len(re.findall(f'{workload_name} Snapshot finished successfully',
                    op.decode().split('<entry>')[1])) == 1:
                LOG.debug("Incremental Snapshot success email sent to user")
                reporting.add_test_step("Incremental Snapshot success email sent to user", tvaultconf.PASS)
            else:
                LOG.error("Incremental Snapshot success email not sent to user")
                reporting.add_test_step("Incremental Snapshot success email sent to user", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            self.delete_vm(vm_id)
            snapshot_id = self.workload_snapshot(wid, True)
            LOG.debug(f"Snapshot ID: {snapshot_id}")
            self.wait_for_workload_tobe_available(wid)
            snapshot_status = self.getSnapshotStatus(wid, snapshot_id)
            LOG.debug(f"Snapshot status: {snapshot_status}")
            if snapshot_status == 'error':
                reporting.add_test_step("Create error snapshot", tvaultconf.PASS)
            else:
                raise Exception("Create error snapshot")
            time.sleep(10)

            cmd = 'curl  -u ' + tvaultconf.setting_data[
                    "smtp_default_recipient"] + ':' + tvaultconf.smtp_password \
                    + ' --silent "https://mail.google.com/mail/feed/atom"'
            op = subprocess.check_output(cmd, shell=True)
            LOG.debug(f"Gmail output: {op}")

            if len(re.findall(f'{workload_name} Snapshot failed',
                    op.decode().split('<entry>')[1])) == 1:
                LOG.debug("Snapshot failure email sent to user")
                reporting.add_test_step("Snapshot failure email sent to user", tvaultconf.PASS)
            else:
                LOG.error("Snapshot failure email not sent to user")
                reporting.add_test_step("Snapshot failure email sent to user", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

            snapshot_id = self.workload_snapshot(wid, False)
            LOG.debug(f"Snapshot ID: {snapshot_id}")
            self.wait_for_workload_tobe_available(wid)
            snapshot_status = self.getSnapshotStatus(wid, snapshot_id)
            LOG.debug(f"Snapshot status: {snapshot_status}")
            if snapshot_status == 'error':
                reporting.add_test_step("Create errored incremental snapshot", tvaultconf.PASS)
            else:
                raise Exception("Create errored incremental snapshot")
            time.sleep(10)

            cmd = 'curl  -u ' + tvaultconf.setting_data[
                    "smtp_default_recipient"] + ':' + tvaultconf.smtp_password \
                    + ' --silent "https://mail.google.com/mail/feed/atom"'
            op = subprocess.check_output(cmd, shell=True)
            LOG.debug(f"Gmail output: {op}")

            if len(re.findall(f'{workload_name} Snapshot failed',
                    op.decode().split('<entry>')[1])) == 1:
                LOG.debug("Incremental Snapshot failure email sent to user")
                reporting.add_test_step("Incremental Snapshot failure email sent to user", tvaultconf.PASS)
            else:
                LOG.error("Incremental Snapshot failure email not sent to user")
                reporting.add_test_step("Incremental Snapshot failure email sent to user", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.add_test_step(str(e), tvaultconf.FAIL)
            reporting.set_test_script_status(tvaultconf.FAIL)
        finally:
            reporting.test_case_to_write()

