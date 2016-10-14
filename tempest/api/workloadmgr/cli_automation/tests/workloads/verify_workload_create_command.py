import unittest
import sys
sys.path.append("/opt/stack/tempest")
from tempest.api.workloadmgr.cli_automation.config import configuration,command_argument_string
from tempest.api.workloadmgr.cli_automation.utils import cli_parser,query_data


class workload_create_command_test(unittest.TestCase):
    def setUp(self):
        self.vm_list = []
        command_test = "nova list | awk -F '|' '{print $2}' | grep -v ID"
        out = cli_parser.cli_output(command_test)
        print out
        for a in out.splitlines():
            if str(a) != "":
                self.vm_list.append(str(a).strip(" "))
        print self.vm_list

    def runTest(self):
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




