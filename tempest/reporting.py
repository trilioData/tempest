from tempest import tvaultconf
import subprocess

test_results_file="/home/deepanshu/tempest_work/tempest/Report/results.html"
test_list_file = "/home/deepanshu/tempest_work/tempest/test-list"
sanity_results_file="test_results"
test_script_status = tvaultconf.PASS
test_script_name = ""
test_step_to_write =""
passed_count = 0
failed_count = 0
total_tests_count = passed_count + failed_count

def setup_report(testname):
    head = """<table border="1">
            <tr bgcolor="#b3e6ff">
                    <th>{0}</th>
                    <th>Result</th>
            </tr>
            """.format(testname)
    with open(test_results_file, "a") as f:
            f.write(head)

def add_test_script(script):
    global test_script_name
    test_script_name = script

def set_test_script_status(status):
   global test_script_status
   test_script_status = status

def test_case_to_write():
    global test_step_to_write
    global test_script_status
    global passed_count
    global failed_count
    global total_tests_count
    if test_script_status == "PASS":
        color = "green"
	passed_count += 1
    else:
        color = "red"
	failed_count += 1
    total_tests_count = passed_count + failed_count
    test_case_to_write = """
	<tr>
		<td colspan="1"><b>{0}</b></td>
		<td> <font color={1}><b>{2}</b></font> </td>
        </tr>
	""".format(test_script_name, color, test_script_status)
    with open(test_results_file, "a") as f:
        f.write(test_case_to_write)
	f.write(test_step_to_write)
    test_step_to_write = ""
    test_script_status = tvaultconf.PASS
    cmd1 = "sed -i -e '9s/passed_count = [0-9]*/passed_count = {0}/' tempest/reporting.py".format(passed_count)
    cmd2 = "sed -i -e '10s/failed_count = [0-9]*/failed_count = {0}/' tempest/reporting.py".format(failed_count)
    cmd = cmd1+"; " +cmd2
    p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE)
    p.wait()

def add_test_step(teststep, status):
    if status == "PASS":
        color = "green"
    else:
        color = "red"
        global test_script_status
        test_script_status = "FAIL"
    global test_step_to_write
    test_step_to_write += """<tr>
                    <td> <font color={1}>{0}</font> </td>
                    <td> <font color={1}>{2}</font> </td>
		 </tr>
                """.format(teststep, color, status)

def end_report_table():
    with open(test_results_file, "a") as f:
        f.write("</table>\n<br>")
    cmd1 = "sed -i -e '14s/<td>[0-9]*/<td>{0}/' Report/results.html".format(total_tests_count)
    cmd2 = "sed -i -e '15s/<b>[0-9]*/<b>{0}/' Report/results.html".format(passed_count)
    cmd3 = "sed -i -e '16s/<b>[0-9]*/<b>{0}/' Report/results.html".format(failed_count)
    cmd = cmd1+"; " +cmd2+"; "+cmd3
    p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE)
    p.wait()

def consolidate_report_table():
    global passed_count
    global failed_count
    global total_tests_count
    consolidate_table = """
	<table border="2">
	    <col width="150">
  	    <col width="150">
            <col width="150">
            <tr bgcolor="#b3ffff">
                    <th colspan="4">Consolidate Report</th>
            </tr>
            <tr>
                    <th>Total</th>
                    <th>Passed</th>
                    <th>Failed</th>
            </tr>
            <tr align="center"> <td>{0}</td>
                 <td><font color=green><b>{1}</b></td>
                 <td><font color=red><b>{2}</b></td>
            </tr>
        </table>
	<br>
        """.format(total_tests_count, passed_count, failed_count)
    with open(test_results_file, "w+") as f:
        f.write(consolidate_table) 

def add_sanity_results(test_step, status):
    with open(sanity_results_file, "a") as f:
	    f.write(str(test_step) + " " + str(status) + "\n")
def get_tests(suite_path):
    import glob
    print suite_path
    print str(suite_path)+"/*.py" 
    for path in glob.glob(str(suite_path)+"*.py"):
	if "__init__" not in path:
	    with open (test_list_file, "a") as f:
		print "test: " + str(path[:-3]).replace("\\",".")+"\n"
		f.write(str(path[:-3]).replace("\\",".")+"\n")
