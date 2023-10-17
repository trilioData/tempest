import yaml
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
            #Create Migration Plan
            self.vms = self.get_migration_test_vms(vm_list= \
                            self.get_vcenter_vms())
            i = 1
            self.plan_id, self.err_str = self.create_migration_plan([self.vms[i]], plan_cleanup=False)
            LOG.debug(f"Plan ID returned from API: {self.plan_id}")
            if self.plan_id and not(self.err_str):
                result_json['Create_Migration_Plan'] = tvaultconf.PASS
            else:
                raise Exception("Create_Migration_Plan")

            #Discover VMs
            self.err_str = self.discover_vms(self.plan_id)
            if self.err_str:
                result_json['Discover_VMs'] = tvaultconf.PASS
            else:
                raise Exception("Discover_VMs")

            #Create cold migration
            self.vm_details = [{'name': tvaultconf.migration_vms[i]['name'] + '_migrated',
                                'id': self.vms[i],
                                'datastore': tvaultconf.migration_vms[i]['datastore']
                               }]
            self.migration_json = self.create_migration_json(self.vm_details, 'cold')
            self.migration_id, self.err_str = self.create_migration(
                                self.plan_id, self.migration_json, migration_cleanup=False)
            LOG.debug(f"Migration ID returned from API: {self.migration_id}")
            if self.migration_id:
                self.wait_for_migrationplan_tobe_available(self.plan_id)
                self.mig_data = self.getMigrationDetails(self.plan_id, self.migration_id)
                self.mig_status = self.getMigrationStatus(self.plan_id, self.migration_id)
                if self.mig_status == 'available':
                    result_json['Create_Cold_Migration'] = tvaultconf.PASS
                else:
                    result_json['Create_Cold_Migration'] = tvaultconf.FAIL
                    result_json['ERROR'] = self.mig_data['error_msg']
            else:
                raise Exception("Create_Cold_Migration")

            #Delete migration
            if self.delete_migration(self.migration_id):
                LOG.debug("Delete migration successful")
            else:
                result_json['Delete_Migration'] = tvaultconf.FAIL

            #Delete migration plan
            self.wait_for_migrationplan_tobe_available(self.plan_id)
            if self.delete_migration_plan(self.plan_id):
                LOG.debug("Delete migration plan successful")
            else:
                result_json['Delete_Migration_Plan'] = tvaultconf.FAIL

        except Exception as e:
            LOG.error("Exception: " + str(e))
            result_json[str(e)] = tvaultconf.FAIL
            result_json['ERROR'] = self.err_str

        finally:
            # Add results to sanity report
            LOG.debug("Finally Result json: " + str(result_json))
            reporting.add_result_json(result_json)
            for k, v in result_json.items():
                reporting.add_sanity_results(k, v)


