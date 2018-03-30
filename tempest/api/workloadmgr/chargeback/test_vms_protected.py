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
        reporting.add_test_script(str(__name__))

    @test.pre_req({'type':'basic_workload'})
    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_chargeback_api(self):
        try:
            if self.exception != "":
                LOG.debug("pre req failed")
                reporting.add_test_step(str(self.exception), tvaultconf.FAIL)
                raise Exception (str(self.exception))
                LOG.debug("pre req completed")  
            
            # Run getVMProtected API :
            vm_protected = self.getVMProtected()
            if not vm_protected:
                reporting.add_test_step("Verified getVMProtected API", tvaultconf.FAIL)
                LOG.debug("getVMProtected API failed")
                raise Exception("getVMProtected API Failed")
            else:
                reporting.add_test_step("Verified getVMProtected API", tvaultconf.PASS)

            # Verify Instance ID :
            vm_id = self.vm_id
            counter = 0
            vm_protected_list = vm_protected['protected_vms']
            for vm in vm_protected_list :
                openstack_vm_id = vm_protected_list[counter]['id']
                LOG.debug(" Openstack VM ID : "+ openstack_vm_id)
                if(vm_id == openstack_vm_id):
                    LOG.debug(" VM ID : "+vm_id)
                    instance_found = True
                else :
                    instance_found = False
                counter = counter + 1
                
            if(instance_found == True ) :
                reporting.add_test_step(" Verified Instance ID ", tvaultconf.PASS)
            else :
                reporting.add_test_step(" Verified Instance ID ", tvaultconf.FAIL)  
            reporting.test_case_to_write()     
        
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

