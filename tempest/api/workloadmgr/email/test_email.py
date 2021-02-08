import subprocess
import shlex
import re
from tempest.util import query_data
from tempest.util import cli_parser
from tempest import command_argument_string
import time
import operator
from tempest import reporting
from tempest import tvaultconf
from oslo_log import log as logging
from tempest.lib import decorators
from tempest import config
from tempest.api.workloadmgr import base
import sys
import os
import json
sys.path.append(os.getcwd())

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()
        reporting.add_test_script(str(__name__))

    @decorators.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_email(self):
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
                    if((str(enable_email_resp['name']) == 'smtp_email_enable') and (str(enable_email_resp['value']) == '1')):
                        reporting.add_test_step(
                            "Enable email notification for project", tvaultconf.PASS)
                        self.wlm_client.client.get(
                            "/workloads/email/test_email")

                        cmd = 'curl  -u ' + tvaultconf.setting_data["smtp_default_recipient"] + ':' + \
                            tvaultconf.tvault_password + ' --silent "https://mail.google.com/mail/feed/atom"'
                        op = subprocess.check_output(cmd, shell=True)
                        if len(re.findall('Testing email configuration',
                                          op.decode().split('<entry>')[1])) == 1:
                            LOG.debug(
                                "Email testing done correctly and email is : {}".format(op))
                            reporting.add_test_step(
                                "Test email", tvaultconf.PASS)
                        else:
                            reporting.add_test_step(
                                "Test email", tvaultconf.FAIL)
                        existing_setting = self.get_settings_list()
                        LOG.debug("Existing setting list: " +
                                  str(existing_setting))

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

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
