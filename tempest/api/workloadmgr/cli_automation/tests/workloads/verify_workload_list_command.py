import unittest
import sys
sys.path.append("/opt/stack/tempest/tempest/api/workloadmgr/cli_automation")
from config import configuration,command_argument_string
from utils import cli_parser,query_data

class workload_list_command_test(unittest.TestCase):
    def runTest(self):
        rc = cli_parser.cli_returncode(command_argument_string.workload_list)
        print rc
        if rc != 0:
            raise Exception("Command did not execute correctly!!!")
        else:
            print ("Command executed correctly!!!")
        wc = query_data.get_available_workloads()
        out = cli_parser.cli_output(command_argument_string.workload_list)
        if (int(wc) == int(out)):
            print "Workload list command listed available workloads correctly"
        else:
            raise Exception ("Workload list command did not list available workloads correctly!!!")



if __name__ == '__main__':
    unittest.main()




