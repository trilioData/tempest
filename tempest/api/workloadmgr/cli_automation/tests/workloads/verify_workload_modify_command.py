import unittest
import sys
sys.path.append("/opt/stack/tempest/tempest/api/workloadmgr/cli_automation")
from config import configuration,command_argument_string
from utils import cli_parser,query_data


class workload_modify_command_test(unittest.TestCase):
    def runTest(self):
        self.workload_id = query_data.get_workload_id(configuration.workload_name)
	print self.workload_id
        workload_modify_name_command = command_argument_string.workload_modify_name + configuration.workload_modify_name + " " +str(self.workload_id)
	print workload_modify_name_command
        rc = cli_parser.cli_returncode(workload_modify_name_command)
        print rc
        if rc != 0:
            raise Exception("Command did not execute correctly!!!")
        else:
            print ("Command executed correctly!!!")
        workload_name = query_data.get_workload_display_name(self.workload_id)
        if (workload_name) == configuration.workload_modify_name:
            print "Workload name has been changed successfully"
        else:
            raise Exception ("Workload name has not been changed!!!")

        workload_modify_description_command = command_argument_string.workload_modify_description + configuration.workload_modify_description + " " + str(self.workload_id)
        print workload_modify_description_command
	rc = cli_parser.cli_returncode(workload_modify_description_command)
        print rc
        if rc != 0:
            raise Exception("Command did not execute correctly!!!")
        else:
            print ("Command executed correctly!!!")
        workload_description = query_data.get_workload_display_description(self.workload_id)
        if (workload_description) == configuration.workload_modify_description:
            print "Workload description has been changed successfully"
        else:
            raise Exception("Workload description has not been changed!!!")

    def tearDown(self):
        workload_modify_name_command = command_argument_string.workload_modify_name + configuration.workload_name + " " + str(self.workload_id)
        rc = cli_parser.cli_returncode(workload_modify_name_command)
        print rc
        if rc != 0:
            raise Exception("Command did not execute correctly!!!")
        else:
            print ("Command executed correctly!!!")



if __name__ == '__main__':
    unittest.main()




