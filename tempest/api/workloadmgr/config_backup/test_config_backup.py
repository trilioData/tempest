import sys
import os
sys.path.append(os.getcwd())
from tempest.api.workloadmgr import base
from tempest import config
from tempest import test
from oslo_log import log as logging
from tempest import tvaultconf
from tempest import reporting
import time
from tempest import command_argument_string
from tempest.util import cli_parser
from tempest.util import query_data

LOG = logging.getLogger(__name__)
CONF = config.CONF

class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()
        cls.client = cls.os.wlm_client

    @test.pre_req({'type':'config_backup'})
    @test.attr(type='smoke')
    @test.idempotent_id('9fe07170-912e-49a5-a629-5f52eeada4c9')
    def test_config_backup(self):
	reporting.add_test_script(str(__name__)+ "_default and  + added_dir")
	try:
	    # prerequisite handles config_user creation and config_backup_pvk(private key) creation
            
            # for config backup configuration, yaml_file creation 
	    added_dir = {'tvault-contego':{'config_dir':['/etc/tvault-contego/']}}
            self.create_config_backup_yaml(added_dir = added_dir)

            # config backup configuration with CLI command
            config_workload_command = command_argument_string.config_workload_configure + " --config-file yaml_file.yaml --authorized-key config_backup_pvk "
    
            LOG.debug("config workload configure cli command: " + str(config_workload_command))
    
            rc = cli_parser.cli_returncode(config_workload_command)
            if rc != 0:
                reporting.add_test_step("Triggering config_workload_configure command via CLI", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step("Triggering config_workload_configure command via CLI", tvaultconf.PASS)
                LOG.debug("Command executed correctly")
	    

	    # config_workload_md5sum_before_backup
	    config_workload_md5sum_before_backup = self.calculate_md5_config_backup()
	    LOG.debug("config_workload_md5sum_before_backup: " + str(config_workload_md5sum_before_backup))

	    # config backup with api
	    config_backup_id = self.create_config_backup()
	        
	    if config_backup_id:
                reporting.add_test_step("Config backup via API", tvaultconf.PASS)
	        LOG.debug("Config backup successful, Config_backup_id: " + str(config_backup_id))
	        LOG.debug("Config backup via api successful")
            else:
                reporting.add_test_step("Config backup via API", tvaultconf.FAIL)
                LOG.debug("Config backup via api unsuccessful")

	    # config_workload_md5sum_after_backup
	    config_workload_md5sum_after_backup = self.calculate_md5_config_backup()
	    LOG.debug("config_workload_md5sum_after_backup: " + str(config_workload_md5sum_after_backup))

	    for i in range(len(config_workload_md5sum_before_backup.keys())):
	        if config_workload_md5sum_before_backup.values()[i][0] == config_workload_md5sum_after_backup.values()[i][0] or config_workload_md5sum_before_backup.values()[i][0] in config_workload_md5sum_after_backup.values()[i][0]:
		    LOG.debug("Config backup md5 verification: " + str(config_workload_md5sum_before_backup.keys()[i]) + " : " + config_workload_md5sum_before_backup.values()[i][0] + " equal to " + config_workload_md5sum_after_backup.values()[i][0])
	            reporting.add_test_step("Config backup md5 verification: config_dir : " + str(config_workload_md5sum_before_backup.keys()[i]), tvaultconf.PASS)
	        else:
	            reporting.add_test_step("Config backup md5 verification: config_dir : " + str(config_workload_md5sum_before_backup.keys()[i]), tvaultconf.FAIL)
	            LOG.debug("Config backup md5 verification: " + str(config_workload_md5sum_before_backup.keys()[i]) + " : " + config_workload_md5sum_before_backup.values()[i][0] + " not equal to " + config_workload_md5sum_after_backup.values()[i][0])


	    # test config_backup_list
            config_backup_list_output = self.get_config_backup_list()

	    LOG.debug("config_backup list output: " + str(config_backup_list_output))

	    if config_backup_list_output != "":
	    	reporting.add_test_step("Config_backup_list", tvaultconf.PASS)
	    else:
		reporting.add_test_step("Config_backup_list", tvaultconf.FAIL)

            config_backups_list = config_backup_list_output['backups']
	     
	    config_backup_found = False
	    
	    for backup in config_backups_list:
            	if backup['id'] == config_backup_id:
		    config_backup_found = True
                    LOG.debug("config_backup_id found in config_backups_list")
                    

	    if config_backup_found:
		reporting.add_test_step("config_backup_id in config_backups_list", tvaultconf.PASS)
            else:
                LOG.debug("config_backup_id not found in config_backups_list")
                reporting.add_test_step("config_backup_id in config_backups_list", tvaultconf.FAIL)
	    
	    # test config_backup_show 
	    config_backup_details = self.show_config_backup(config_backup_id)

	    if config_backup_details != "":
                reporting.add_test_step("Config_backup_show", tvaultconf.PASS)
            else:
                reporting.add_test_step("Config_backup_show", tvaultconf.FAIL)

	    # test_config_backup_delete
	    if self.delete_config_backup(config_backup_id):
		reporting.add_test_step("Config_backup_delete", tvaultconf.PASS)
	    else:
	    	reporting.add_test_step("Config_backup_delete", tvaultconf.FAIL)

	    reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
    
