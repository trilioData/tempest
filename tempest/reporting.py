from tempest import tvaultconf
import subprocess
import datetime
import os
import pickle

test_results_file="Report/results.html"
test_results_temp = "Report/temp_results"
test_reports_file = "Report/test_reports"
sanity_results_file="test_results"
test_script_status = tvaultconf.PASS
test_script_name = ""
test_step_to_write =""
passed_count = 0
failed_count = 0
total_tests_count = passed_count + failed_count
steps_count = 0
case_count = 0
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
    global steps_count
    steps_count = 0
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
    global case_count
    case_count+=1
    total_tests_count = passed_count + failed_count
    consolidate_report_table()
    test_case_to_write = """
	<tr>
		<td colspan="1"><b>{3}. {0}</b></td>
		<td> <font color={1}><b>{2}</b></font> </td>
        </tr>
	""".format(test_script_name, color, test_script_status, case_count)
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
    global steps_count
    steps_count+=1
    test_step_to_write += """<tr>
                    <td> <font color={1}>{3}. {0}</font> </td>
                    <td> <font color={1}>{2}</font> </td>
		 </tr>
                """.format(teststep, color, status, steps_count)

def end_report_table():
    with open(test_results_file, "a") as f:
        f.write("</table>\n<br>")
    cmd1 = "sed -i -e '14s/<td>[0-9]*/<td>{0}/' Report/results.html".format(total_tests_count)
    cmd2 = "sed -i -e '15s/<b>[0-9]*/<b>{0}/' Report/results.html".format(passed_count)
    cmd3 = "sed -i -e '16s/<b>[0-9]*/<b>{0}/' Report/results.html".format(failed_count)
    cmd = cmd1+"; " +cmd2+"; "+cmd3
    p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE)
    p.wait()
    global case_count
    case_count = 0

def gather_reports():
    with open(test_results_temp, 'rb') as f1:
        ogdata = pickle.load(f1)
    if os.path.exists(test_reports_file):
        with open(test_reports_file, 'rb') as f2:
            data = pickle.load(f2)
            data = data + ogdata
        with open(test_reports_file, 'wb') as f3:
            pickle.dump(data, f3)
    else:
        with open(test_reports_file, 'wb') as f4:
            pickle.dump(ogdata, f4)

def consolidate_report():
    with open(test_reports_file,'rb') as f1:
        vals = pickle.load(f1)
        valscopy = [vals[i:i + 3] for i in xrange(0, len(vals), 3)]
        results = [sum(i) for i in zip(*valscopy)]
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
            """.format(results[0], results[1], results[2])
    with open(test_results_file, 'r') as f2:
        ogcontent = f2.read()
    with open(test_results_file,'w') as f3:
        f3.write(consolidate_table)
    with open(test_results_file,'a') as f4:
        f4.write(ogcontent)
    os.remove(test_results_temp)
    os.remove(test_reports_file)

def consolidate_report_table():
    global passed_count
    global failed_count
    global total_tests_count
    with open(test_results_temp, 'wb') as f:
        data = [total_tests_count, passed_count, failed_count]
        pickle.dump(data, f)

def add_sanity_results(test_step, status):
    with open(sanity_results_file, "a") as f:
	    f.write(str(test_step) + " " + str(status) + "\n")

def get_tests(test_list_file,suite_path):
    import glob
    with open (test_list_file, "w") as f:
        for path in glob.glob(str(suite_path)+"/*.py"):
            if "__init__" not in path:
                print "test: " + ".".join(str(path[:-3]).split("/")[7:])+"\n"
                f.write(".".join(str(path[:-3]).split("/")[7:])+"\n")

def add_sanity_results_to_tempest_report():
    result_table = """ <table border="1"><tr><th>TestName</th><th>Result</th></tr>"""
    with open(sanity_results_file, "r") as f:
        for line in f:
            if(line == "\n"):
                pass
            else:
                row = line.split()
                test_name = str(row[0])
                test_result = str(row[1])
                if(line.startswith("ERROR")):
                    text_color = "red"
                    test_result = line[6:]
                elif(test_result.startswith("FAIL")):
                    text_color = "red"
                else:
                    text_color = "green"
                result_table+="""<tr>
                    <td><font color="%s">%s</font></td>
                    <td><font color="%s">%s</font></td>
                    </tr> """ % (text_color, test_name, text_color, test_result)
    html_file=open(test_results_file, "a")
    result_table+="""</table>"""
    html_file.write("Date : " + str(datetime.datetime.now()))
    html_file.write("<br/>")
    html_file.write("<b>Sanity Test Results</b>")
    html_file.write("<br/><br/>")
    html_file.write(result_table)
    html_file.close()
 
