from tempest.api.workloadmgr import base
from tempest import config
from tempest.lib import decorators
from oslo_log import log as logging
from tempest import tvaultconf
from tempest import reporting

LOG = logging.getLogger(__name__)
CONF = config.CONF

class WorkloadsTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadsTest, cls).setup_clients()

    @decorators.attr(type='workloadmgr_api')
    def test_sanity(self):
        try:
            result_json = {}
            self.vms = self.get_migration_test_vms(vm_list= \
                            self.get_vcenter_vms())
            self.plan_id = self.create_migration_plan([self.vms[0]])
            LOG.debug(f"Plan ID returned from API: {self.plan_id}")
            if self.plan_id:
                result_json['Create_Migration_Plan'] = tvaultconf.PASS
            else:
                raise Exception("Create_Migration_Plan")

        except Exception as e:
            LOG.error("Exception: " + str(e))
            result_json[str(e)] = tvaultconf.FAIL

        finally:
            # Add results to sanity report
            LOG.debug("Finally Result json: " + str(result_json))
            reporting.add_result_json(result_json)
            for k, v in result_json.items():
                reporting.add_sanity_results(k, v)

