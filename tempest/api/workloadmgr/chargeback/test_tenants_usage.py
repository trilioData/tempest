from tempest.api.workloadmgr import base
from tempest import config
from tempest import test
from tempest import prerequisites
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

    @test.attr(type='smoke')
    @test.idempotent_id('9fe07175-912e-49a5-a629-5f52eeada4c9')
    def test_tenants_usage(self):
        try:
            # Run getTenantUsage API
             
            Tenant_Usage = self.getTenantUsage()
            global_usage_total_vms = Tenant_Usage['global_usage']['total_vms']
            LOG.debug(" Total VM In Openstack  : "+ str(global_usage_total_vms))
            tenants_usage_vms_protected = Tenant_Usage['tenants_usage'][str(CONF.identity.tenant_id)]['vms_protected']
            LOG.debug(" VM Procted in Tenant : "+ str(tenants_usage_vms_protected))

            # Run Prereqisite 
           
	    prerequisites.basic_workload(self)
            if self.exception != "":
                LOG.debug("pre req failed")
                reporting.add_test_step(str(self.exception), tvaultconf.FAIL)
                raise Exception (str(self.exception))
            LOG.debug("pre req completed")

            # Get the openstack global and tenant usage after creating instance and workload

            Tenant_Usage_after_prereqisite = self.getTenantUsage()
            global_usage_total_vms_after_pre_req =  Tenant_Usage_after_prereqisite['global_usage']['total_vms']
            LOG.debug(" Total vms in opensatck after prereqisite run : "+ str(global_usage_total_vms_after_pre_req))
            tenants_usage_vms_protected_after_pre_req = Tenant_Usage_after_prereqisite['tenants_usage'][CONF.identity.tenant_id]['vms_protected']
            LOG.debug(" No. of vms protected after prerequisite : "+ str(tenants_usage_vms_protected_after_pre_req))

            # Verify Global Usage
            if ( (global_usage_total_vms + 1 ) == global_usage_total_vms_after_pre_req ):
                LOG.debug(" Global usage total vms value is correct ")
                reporting.add_test_step("Verify total vms in openstack", tvaultconf.PASS)
            else :
                LOG.debug(" Total vms in openstack is incorrect" )
                reporting.add_test_step("Verify total vms in openstack", tvaultconf.FAIL)
		raise Exception(" Verification for total vms in openstack failed ")
                  
            # Verify Global Usage
            if ( ( tenants_usage_vms_protected + 1 )  == tenants_usage_vms_protected_after_pre_req ):
                LOG.debug(" No. of total protected vms in tenant is correct " )
                reporting.add_test_step(" Verify total protected vms in tenant ", tvaultconf.PASS)
            else :
                LOG.debug(" No. of total protected vms in tenant is incorrect" )
                reporting.add_test_step(" Verify total protected vms in tenant", tvaultconf.FAIL)
	        raise Exception(" Verification for protected vms in tenant failed ")

            reporting.test_case_to_write()         
 
        except Exception as e:
            LOG.error("Exception: " + str(e))
            reporting.set_test_script_status(tvaultconf.FAIL)
            reporting.test_case_to_write()

