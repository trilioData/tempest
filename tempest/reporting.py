from tempest import tvaultconf
import subprocess
import datetime
import os
import pickle

test_results_file = "Report/results.html"
sanity_results_file = "test_results"
sanity_stats_file = "test_stats"
test_script_status = tvaultconf.PASS
test_script_name = ""
test_step_to_write = ""
passed_count = 0
failed_count = 0
total_tests_count = passed_count + failed_count
steps_count = 0


def setup_report(testname):
    head = """<table border="1">
            <tr bgcolor="#b3e6ff">
                    <th style="font-size:20px">{0}</th>
                    <th style="font-size:20px">Result</th>
            </tr>
            """.format(testname.capitalize())
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
    total_tests_count = passed_count + failed_count
    test_case_to_write = """
	<tr>
		<td colspan="1" style="font-size:15px"><b>{0}</b></td>
		<td> <font color={1} style="font-size:15px"><b>{2}</b></font> </td>
        </tr>
	""".format(test_script_name, color, test_script_status)
    with open(test_results_file, "a") as f:
        f.write(test_case_to_write)
        f.write(test_step_to_write)
    test_step_to_write = ""
    test_script_status = tvaultconf.PASS
    cmd1 = "sed -i -e '9s/passed_count = [0-9]*/passed_count = {0}/' tempest/reporting.py".format(
        passed_count)
    cmd2 = "sed -i -e '10s/failed_count = [0-9]*/failed_count = {0}/' tempest/reporting.py".format(
        failed_count)
    cmd = cmd1 + "; " + cmd2
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
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
    steps_count += 1
    test_step_to_write += """<tr>
                    <td> <font color={1}><pre style="font-family: 'Times New Roman', Times, serif; font-size: 13px; height: 17px"><i>    {3}. {0}</pre></font> </td>
                    <td> <font color={1} style="font-size:15px">{2}</font> </td>
		 </tr>
                """.format(teststep.capitalize(), color, status, steps_count)


def end_report_table():
    with open(test_results_file, "a") as f:
        f.write("</table>\n<br>")
    cmd1 = "sed -i -e '14s/<td>[0-9]*/<td>{0}/' Report/results.html".format(
        total_tests_count)
    cmd2 = "sed -i -e '15s/<b>[0-9]*/<b>{0}/' Report/results.html".format(
        passed_count)
    cmd3 = "sed -i -e '16s/<b>[0-9]*/<b>{0}/' Report/results.html".format(
        failed_count)
    cmd = cmd1 + "; " + cmd2 + "; " + cmd3
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    p.wait()


def consolidate_report():
    pass_count = 0
    fail_count = 0
    with open(test_results_file, 'r') as html_file:
        for line in html_file:
            if 'PASS' in line:
                if '<b>' in line:
                    pass_count += 1
            if 'FAIL' in line:
                if '<b>' in line:
                    fail_count += 1
    total_count = pass_count + fail_count

    consolidate_table = """
        <table border="2">
            <col width="150">
            <col width="150">
                <col width="150">
                <tr bgcolor="#b3ffff">
                        <th colspan="4" style="font-size:19px">Consolidated Report</th>
                </tr>
                <tr>
                        <th style="font-size:17px">Total</th>
                        <th style="font-size:17px">Passed</th>
                        <th style="font-size:17px">Failed</th>
                </tr>
                <tr align="center"> <td style="font-size:17px">{0}</td>
                     <td><font color=green style="font-size:17px"><b>{1}</b></td>
                     <td><font color=red style="font-size:17px"><b>{2}</b></td>
                </tr>
            </table>
        <br>
            """.format(total_count, pass_count, fail_count)
    with open(test_results_file, 'r') as f2:
        ogcontent = f2.read()
    with open(test_results_file, 'w') as f3:
        f3.write(consolidate_table)
    styl = '''
    <style>
         pre {
            overflow-x: auto;
            white-space: pre-wrap;
            white-space: -moz-pre-wrap;
            white-space: -pre-wrap;
            white-space: -o-pre-wrap;
            word-wrap: break-word;
         }
      </style>
    '''
    with open(test_results_file, 'a') as f4:
        f4.write(styl)
        f4.write(ogcontent)

    from bs4 import BeautifulSoup
    with open(test_results_file, 'r') as f:
        soup = BeautifulSoup(f, 'html.parser')
    l1 = soup.findAll('table', {'border': '1'})
    for each in l1:
        i = 1
        children = each.findChildren('b')
        for child in children:
            if child.string != 'FAIL' and child.string != 'PASS':
                child.string = "{}. ".format(i) + child.string
                i += 1
    with open(test_results_file, "wb") as f_output:
        f_output.write(soup.encode('utf8'))


def add_sanity_results(test_step, status):
    with open(sanity_results_file, "a") as f:
        f.write(str(test_step) + " " + str(status) + "\n")


def get_tests(test_list_file, suite_path):
    import glob
    with open(test_list_file, "w") as f:
        for path in glob.glob(str(suite_path) + "/*.py"):
            if "__init__" not in path:
                print(
                    "test: " + ".".join(str(path[:-3]).split("/")[-5:]) + "\n")
                f.write(".".join(str(path[:-3]).split("/")[-5:]) + "\n")


def add_sanity_results_to_tempest_report():
    result_table = """ <table border="1"><tr><th>TestName</th><th>Result</th></tr>"""
    with open(sanity_results_file, "r") as f:
        for line in f:
            if(line == "\n" or line.find('---') != -1):
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
                result_table += """<tr>
                    <td><font color="%s" style="font-size:15px">%s</font></td>
                    <td><font color="%s" style="font-size:15px">%s</font></td>
                    </tr> """ % (text_color, test_name, text_color, test_result)
    html_file = open(test_results_file, "a")
    result_table += """</table>"""
    html_file.write("Date : " + str(datetime.datetime.now()))
    html_file.write("<br/>")
    html_file.write("<b>Sanity Test Results</b>")
    html_file.write("<br/><br/>")
    html_file.write(result_table)
    html_file.close()


def add_sanity_stats(workload_type, name, data):
    with open(sanity_stats_file, "a") as f:
        f.write(str(workload_type) + " " str(name) + " " + str(data) + "\n")


def add_sanity_stats_to_tempest_report():
    stat_table = """ <table border="1"><tr><th>WorkloadType</th>
            <th>Name</th><th>Data</th></tr>"""
    with open(sanity_stats_file, "r") as f:
        for line in f:
            if(line == "\n" or line.find('---') != -1):
                pass
            else:
                row = line.split()
                workload_type = str(row[0])
                name = str(row[1])
                data = str(row[2])
                stat_table += """<tr>
                    <td><style="font-size:15px">%s</td>
                    <td><style="font-size:15px">%s</td>
                    <td><style="font-size:15px">%s</td>
                    </tr> """ % (workload_type, name, data)
    html_file = open(test_results_file, "a")
    stat_table += """</table>"""
    html_file.write("<br/><br/>")
    html_file.write("<b>Sanity Test Run Statistics</b>")
    html_file.write("<br/><br/>")
    html_file.write(stat_table)
    html_file.close()
