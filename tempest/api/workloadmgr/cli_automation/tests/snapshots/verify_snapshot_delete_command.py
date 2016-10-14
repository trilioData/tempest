import unittest
import sys
from time import sleep
sys.path.append("/opt/stack/tempest")
from tempest.api.workloadmgr.cli_automation.config import configuration,command_argument_string
from tempest.api.workloadmgr.cli_automation.utils import cli_parser,query_data


class snapshot_delete_command_test(unittest.TestCase):
    def runTest(self):
        self.deleted = False
        rc = cli_parser.cli_returncode(command_argument_string.snapshot_delete)
        print rc
        if rc != 0:
            raise Exception("Command did not execute correctly!!!")
        else:
            print ("Command executed correctly!!!")
        wc = query_data.get_workload_snapshot_delete_status(configuration.snapshot_name,configuration.snapshot_type_full)

        while (str(wc) != "deleted"):
            sleep (5)
            wc = query_data.get_workload_snapshot_delete_status(configuration.snapshot_name, configuration.snapshot_type_full)
            if (str(wc) == "deleted"):
                print "Workload snapshot successfully deleted"
                self.deleted = True
                break
        if (self.deleted == False):
            raise Exception ("Snapshot did not get deleted")



if __name__ == '__main__':
    unittest.main()




