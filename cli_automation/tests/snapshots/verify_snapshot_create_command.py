import unittest
import sys
from time import sleep
sys.path.append("/opt/stack/tempest/cli_automation")
from cliconfig import configuration,command_argument_string
from utils import cli_parser,query_data

class snapshot_create_command_test(unittest.TestCase):
    def runTest(self):
        self.created = False
        rc = cli_parser.cli_returncode(command_argument_string.snapshot_create)
        print rc
        if rc != 0:
            raise Exception("Command did not execute correctly!!!")
        else:
            print ("Command executed correctly!!!")
        wc = query_data.get_workload_snapshot_status(configuration.snapshot_name,configuration.snapshot_type_full)
        while (str(wc) != "available" or str(wc)!= "error"):
            sleep (5)
            wc = query_data.get_workload_snapshot_status(configuration.snapshot_name, configuration.snapshot_type_full)
            if (str(wc) == "available"):
                print "Workload snapshot successfully completed"
                self.created = True
                break
            else:
                if (str(wc) == "error"):
                    break
        if (self.created == False):
            raise Exception ("Workload snapshot did not get created!!!")


if __name__ == '__main__':
    unittest.main()




