import unittest
import sys
from time import sleep
sys.path.append("/opt/stack/tempest/tempest/api/workloadmgr/cli_automation")
from config import configuration,command_argument_string
from utils import cli_parser,query_data

class workload_delete_command_test(unittest.TestCase):
    def runTest(self):
        self.deleted = False
        rc = cli_parser.cli_returncode(command_argument_string.workload_delete)
        print rc
        if rc != 0:
            raise Exception("Command did not execute correctly!!!")
        else:
            print ("Command executed correctly!!!")
        wc = query_data.get_deleted_workload(configuration.workload_name)
        while (str(wc) != "deleted"):
            sleep (5)
            wc = query_data.get_deleted_workload(configuration.workload_name)
            if (str(wc) == "deleted"):
                print "Workload successfully deleted"
                self.deleted = True
                break
        if (self.deleted == False):
            raise Exception ("Workload did not get deleted")

if __name__ == '__main__':
    unittest.main()
