import unittest
import sys
import os

sys.path.append(os.getcwd())

from utils import HTMLTestRunner
from tests.snapshots import verify_snapshot_list_command,verify_snapshot_create_command,verify_snapshot_delete_command
from tests.restores import verify_restore_list_command,verify_oneclickrestore_command,verify_selectiverestore_command
from tests.workloads import verify_workload_list_command,verify_workload_create_command,verify_workload_delete_command,verify_workload_modify_command

runType = "run" + "Test"

'''
Function definition to create a test suite
'''


def pyTestSuite():
    objSuite = unittest.TestSuite()
    # Add test cases to the test suite
    objSuite.addTest(verify_workload_create_command.workload_create_command_test(runType))
    objSuite.addTest(verify_workload_list_command.workload_list_command_test(runType))
    objSuite.addTest(verify_workload_modify_command.workload_modify_command_test(runType))

    objSuite.addTest(verify_snapshot_create_command.snapshot_create_command_test(runType))
    objSuite.addTest(verify_snapshot_list_command.snapshot_list_command_test(runType))

    objSuite.addTest(verify_oneclickrestore_command.restore_oneclick_command_test(runType))
    objSuite.addTest(verify_restore_list_command.restore_list_command_test(runType))
    #objSuite.addTest(verify_selectiverestore_command.restore_selective_command_test(runType))

    objSuite.addTest(verify_snapshot_delete_command.snapshot_delete_command_test(runType))
    objSuite.addTest(verify_workload_delete_command.workload_delete_command_test(runType))

    return objSuite


'''
Create Test Suite
'''
objTestSuite = pyTestSuite()

'''
Execute the test suite
'''
curDir = os.getcwd()

import time
timestr = time.strftime("%Y%m%d-%H%M%S")
outfile = open(curDir + "/Reports/TestReport"+timestr+".html","w")
print
runner = HTMLTestRunner.HTMLTestRunner(
    stream=outfile,
    title='CLI Automation Report',
    description='CLI Test Automation Report')
runner.run(objTestSuite)
