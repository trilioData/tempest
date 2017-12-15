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
    config_backup_id = None

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()
        cls.client = cls.os.wlm_client

    @test.pre_req({'type':'config_backup'})
    @test.attr(type='smoke')
    @test.idempotent_id('9fe07170-912e-49a5-a629-5f52eeada4c9')
    def test_1_config_backup(self):
	global config_backup_id
	reporting.add_test_script(str(__name__)+ "_default + added_dir: cli")
	try:
	    # prerequisite handles config_user creation and config_backup_pvk(private key) creation and config_workload configuration

	    config_workload_md5sum_before_backup = self.calculate_md5_config_backup(added_dir=tvaultconf.additional_dir)
	    LOG.debug("config_workload_md5sum_before_backup: " + str(config_workload_md5sum_before_backup))
	    
	    #config backup configuration with CLI command
            config_backup_command = command_argument_string.config_backup 

            LOG.debug("config backup cli command: " + str(config_backup_command))

            rc = cli_parser.cli_returncode(config_backup_command)
            if rc != 0:
                reporting.add_test_step("Triggering config_backup command via CLI", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step("Triggering config_backup command via CLI", tvaultconf.PASS)
                LOG.debug("Command executed correctly")
	    
	    time.sleep(10)
	    config_backup_id = query_data.get_config_backup_id()
            LOG.debug("Config backup id: " + str(config_backup_id))

	    if(config_backup_id != None):
	        status  = self.wait_for_config_backup_tobe_available(config_backup_id)
	        if status == "available":
	            LOG.debug("config backup detials: " + str(self.show_config_backup(config_backup_id)))
                    reporting.add_test_step("Config Backup", tvaultconf.PASS)
	        else:
                    reporting.add_test_step("Config Backup", tvaultconf.FAIL)
                    reporting.set_test_script_status(tvaultconf.FAIL)
	    else:
	        reporting.add_test_step("Config Backup", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)     
	        raise Exception("Config Backup Failed.")  
	 
	    config_workload_md5sum_after_backup = self.calculate_md5_config_backup(added_dir=tvaultconf.additional_dir)
	    LOG.debug("config_workload_md5sum_after_backup: " + str(config_workload_md5sum_after_backup))

	    if config_workload_md5sum_before_backup == config_workload_md5sum_after_backup :
		reporting.add_test_step("Config backup md5 verification", tvaultconf.PASS)
	    else:
		reporting.add_test_step("Config backup md5 verification", tvaultconf.FAIL)
		reporting.set_test_script_status(tvaultconf.FAIL)
	    
	    vault_storage_path = self.show_config_backup(config_backup_id)['config_backup']['vault_storage_path'].rstrip()

	    compute_hostname = self.get_compute_hostname().rstrip()

	    config_workload_md5sum_after_backup_vault_storage = self.calculate_md5_config_backup(vault_storage_path=vault_storage_path, compute_hostname=compute_hostname, added_dir=tvaultconf.additional_dir)
	    LOG.debug("config_workload_vault_md5_sum_vault_storage: "+ str(config_workload_md5sum_after_backup_vault_storage))

            if config_workload_md5sum_before_backup == config_workload_md5sum_after_backup_vault_storage:
                reporting.add_test_step("Config backup md5 verification : vault_storage", tvaultconf.PASS)
            else:
                reporting.add_test_step("Config backup md5 verification: vault_storage", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)

	    reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    
    @test.attr(type='smoke')
    @test.idempotent_id('9fe07170-912e-49a5-a629-5f52eeada4c9')
    def test_2_config_backup_list(self):
        global config_backup_id
        reporting.add_test_script(str(__name__)+ "_config_backup_list: api")
        try:  

            # test config_backup_list
            config_backup_list_output = self.get_config_backup_list()

            LOG.debug("config_backup list output: " + str(config_backup_list_output))

            if config_backup_list_output != "":
            	reporting.add_test_step("Config_backup_list", tvaultconf.PASS)
            else:
        	reporting.add_test_step("Config_backup_list", tvaultconf.FAIL)

            config_backups_list = config_backup_list_output['backups']
             
            config_backup_found = False
            LOG.debug("Finding config backup id: " + str(config_backup_id))
            for backup in config_backups_list:
            	if backup['id'] == str(config_backup_id):
        	    config_backup_found = True
                    LOG.debug("config_backup_id found in config_backups_list")
        	    break
                    
            if config_backup_found:
        	reporting.add_test_step("config_backup_id in config_backups_list", tvaultconf.PASS)
            else:
                LOG.debug("config_backup_id not found in config_backups_list")
                reporting.add_test_step("config_backup_id in config_backups_list", tvaultconf.FAIL)

            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
            

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07170-912e-49a5-a629-5f52eeada4c9')
    def test_3_config_backup_show(self):
        global config_backup_id
        reporting.add_test_script(str(__name__)+ "_config_backup_show: cli")
        try:
            # test config_backup_show 
            config_backup_show_command = command_argument_string.config_backup_show + " " + str(config_backup_id)

            LOG.debug("config backup show cli command: " + str(config_backup_show_command))

            rc = cli_parser.cli_returncode(config_backup_show_command)
            if rc != 0:
                reporting.add_test_step("Triggering config_backup_show command via CLI", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step("Triggering config_backup_show command via CLI", tvaultconf.PASS)
                LOG.debug("Command executed correctly")
            
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07170-912e-49a5-a629-5f52eeada4c9')
    def test_4_config_backup_delete(self):
        global config_backup_id
        reporting.add_test_script(str(__name__)+ "_config_backup_delete: cli")
        try:
            # test_config_backup_delete

            # config backup configuration with CLI command
            config_backup_delete_command = command_argument_string.config_backup_delete + " " + str(config_backup_id)

            LOG.debug("config backup delete cli command: " + str(config_backup_delete_command))

            rc = cli_parser.cli_returncode(config_backup_delete_command)
            if rc != 0:
                reporting.add_test_step("Triggering config_backup_delete command via CLI", tvaultconf.FAIL)
                raise Exception("Command did not execute correctly")
            else:
                reporting.add_test_step("Triggering config_backup_delete command via CLI", tvaultconf.PASS)
                LOG.debug("Command executed correctly")

            config_backup_id_after_deletion = query_data.get_config_backup_id()
            LOG.debug("Config backup id after: " + str(config_backup_id_after_deletion))

            if config_backup_id_after_deletion == config_backup_id:
                reporting.add_test_step("Config Backup Deletion", tvaultconf.FAIL)
                reporting.set_test_script_status(tvaultconf.FAIL)
            else:
        	reporting.add_test_step("Config Backup Deletion", tvaultconf.PASS)

	    # delete config_user
	    self.delete_config_user()
            
            reporting.test_case_to_write()

        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
    
