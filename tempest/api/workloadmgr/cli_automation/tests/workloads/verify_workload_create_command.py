import unittest
import sys
sys.path.append("/opt/stack/tempest")
from tempest.api.workloadmgr.cli_automation.config import configuration
from tempest.api.workloadmgr.cli_automation.utils import cli_parser,query_data


class workload_create_command_test(unittest.TestCase):
    def setUp(self):
        self.vm_list = []
        self.available_vms = []
        command_test = "nova list | awk -F '|' '{print $2}' | grep -v ID"
        out = cli_parser.cli_output(command_test)
        print out
        for a in out.splitlines():
            if str(a) != "":
                self.vm_list.append(str(a).strip(" "))
        print self.vm_list
        self.workload_vmlist = query_data.get_vmids()
        for vm in self.vm_list:
            if vm not in self.workload_vmlist:
                    self.available_vms.append(vm)
        print self.available_vms
        if len(self.available_vms) > 0:
            configuration.instance_id = self.available_vms[0]
        else:
            raise Exception ("No available instance for creating new workload")


    def runTest(self):
        from tempest.api.workloadmgr.cli_automation.config import command_argument_string
        rc = cli_parser.cli_returncode(command_argument_string.workload_create)
        print rc
        if rc != 0:
            raise Exception("Command did not execute correctly!!!")
        else:
            print ("Command executed correctly!!!")
        wc = query_data.get_workload_count(configuration.workload_name)
        if (int(wc)>0):
            print "Workload has been created successfully"
        else:
            raise Exception ("Workload not present!!!")

if __name__ == '__main__':
    unittest.main()




