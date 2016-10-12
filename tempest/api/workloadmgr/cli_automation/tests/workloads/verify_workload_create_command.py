import unittest
import sys
sys.path.append("/root/cli_automation")
from cli_automation.config import configuration,command_argument_string
from cli_automation.utils import cli_parser,query_data


class workload_create_command_test(unittest.TestCase):
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




