import unittest
import sys
sys.path.append("/root/cli_automation")
from config import command_argument_string
from utils import cli_parser,query_data

class restore_list_command_test(unittest.TestCase):
    def runTest(self):
        rc = cli_parser.cli_returncode(command_argument_string.restore_list)
        print rc
        if rc != 0:
            raise Exception("Command did not execute correctly!!!")
        else:
            print ("Command executed correctly!!!")
        wc = query_data.get_available_restores()
        out = cli_parser.cli_output(command_argument_string.restore_list)
        if (int(wc) == int(out)):
            print "Restore list command listed available restores correctly"
        else:
            raise Exception ("Restore list command did not list available restores correctly!!!")



if __name__ == '__main__':
    unittest.main()




