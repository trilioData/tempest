import unittest
import sys
from time import sleep
sys.path.append("/opt/stack/tempest/cli_automation")
from cliconfig import configuration,command_argument_string
from utils import cli_parser,query_data


class restore_delete_command_test(unittest.TestCase):
    def runTest(self):
        rc = cli_parser.cli_returncode(command_argument_string.restore_delete)
        print rc
        if rc != 0:
            raise Exception("Command did not execute correctly!!!")
        else:
            print ("Command executed correctly!!!")
        sleep (5)
        wc = query_data.get_snapshot_restore_delete_status(configuration.restore_name,configuration.restore_type)
        print wc
        if (str(wc) == "1"):
            print "Snapshot restore successfully deleted"
        else:
            raise Exception ("Restore did not get deleted")



if __name__ == '__main__':
    unittest.main()
