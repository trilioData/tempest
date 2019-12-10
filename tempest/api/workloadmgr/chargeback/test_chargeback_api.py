from tempest.api.workloadmgr import base
from tempest import config
from tempest import test
from oslo_log import log as logging
from tempest import tvaultconf
from tempest import reporting


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

            vm_id = self.vm_id
            wid = self.wid
            chargeback_info = self.getTenantChargeback()	
	    if not chargeback_info:
		reporting.add_test_step("Verified Chargeback API", tvaultconf.FAIL)
		LOG.debug("Verified Chargeback API failed")
	        raise Exception("Verified Chargeback API Failed")
	    else:
	        reporting.add_test_step("Verified Chargeback API", tvaultconf.PASS)
            workload_id_chargeback = chargeback_info[str(CONF.identity.tenant_id)]['tenant_name']
            LOG.debug(" Env Tenant ID: "+ CONF.identity.tenant_id)
            LOG.debug(" Instance ID : "+ vm_id)
       
            
            #Verify workload ID
            openstack_workload_ids = chargeback_info[CONF.identity.tenant_id]['workloads'].keys()
            LOG.debug(" Workload ID : "+ str(openstack_workload_ids))
            for worklad_id in openstack_workload_ids:
                if ( worklad_id == wid ):
                    LOG.debug(" Workload ID : "+ wid)
                    workload_found = True
            if ( workload_found == True ) :
                reporting.add_test_step(" Verified workload id ", tvaultconf.PASS)
            else :
                reporting.add_test_step(" Verified workload id ", tvaultconf.FAIL)
		raise Exception(" Verification for workload id failed ")

            #Verify Instance ID 
            openstack_instance_ids = chargeback_info[CONF.identity.tenant_id]['workloads'][wid]['protected_vms'].keys()
            LOG.debug(" VM Name : " + openstack_instance_ids[0])
            for instance_id in openstack_instance_ids:
                if ( instance_id == vm_id ):
                    LOG.debug(" VM ID : "+ instance_id)
                    instance_found = True
            if ( instance_found == True ) :
                reporting.add_test_step(" Verified instance id ", tvaultconf.PASS)
            else :
                reporting.add_test_step(" Verified instance id ", tvaultconf.FAIL)
		raise Exception(" Varification for instance id failed ")

	    reporting.test_case_to_write()
	            
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()
