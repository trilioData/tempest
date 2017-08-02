
from oslo_log import log as logging
LOG = logging.getLogger(__name__)

def small_workload(self):
    self.workload_instances = []
    LOG.debug("Running prerequisites for : small_workload")
    vms_per_workload = 1
    for vm in range(0,vms_per_workload):
       vm_id = self.create_vm()
       self.workload_instances.append(vm_id)
