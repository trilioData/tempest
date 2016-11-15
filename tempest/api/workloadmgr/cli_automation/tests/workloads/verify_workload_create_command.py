import unittest
import sys
from time import sleep
sys.path.append("/opt/stack/tempest/tempest/api/workloadmgr/cli_automation")
from cliconfig import configuration
from utils import cli_parser,query_data


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
            #configuration.instance_id = self.available_vms[0]
	    pass
        else:
            raise Exception ("No available instance for creating new workload")


    def runTest(self):

        from cliconfig import command_argument_string
	workload_create = command_argument_string.workload_create + " --instance instance-id=" +str(self.available_vms[0])
	self.created = False
	rc = cli_parser.cli_returncode(workload_create)
        print rc
        if rc != 0:
            raise Exception("Command did not execute correctly!!!")
        else:
            print ("Command executed correctly!!!")
	wc = query_data.get_workload_status(configuration.workload_name)
        while (str(wc) != "available" or str(wc)!= "error"):
            sleep (5)
            wc = query_data.get_workload_status(configuration.workload_name)
            if (str(wc) == "available"):
                print "Workload successfully created"
                self.created = True
                break
            else:
                if (str(wc) == "error"):
                    break
        if (self.created == False):
            raise Exception ("Workload did not get created!!!")


if __name__ == '__main__':
    unittest.main()




