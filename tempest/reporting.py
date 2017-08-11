test_results_file="Report/results.html"
sanity_results_file="test_results"
test_script_status = "PASS"
test_script_name = ""
test_step_to_write =""

def setup_report():
    with open(test_results_file, "a") as f:
        f.seek(10)
        f.truncate()

    head = """<table border="1">
            <tr>
                    <th>TestName</th>
                    <th>Result</th>
            </tr>
            """
    with open(test_results_file, "w+") as f:
            f.write(head)

def add_test_script(script):
    global test_script_name
    test_script_name = script

def test_case_to_write(status):
    global test_step_to_write
    if status == "PASS":
        color = "green"
    else:
        color = "red"
    test_case_to_write = """
	<tr>
		<td colspan="1">{0}</td>
		<td> <font color={1}>{2}</font> </td>
        </tr>
	""".format(test_script_name, color, status)
    with open(test_results_file, "a") as f:
        f.write(test_case_to_write)
	f.write(test_step_to_write)

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
        f.write("</table>")

def add_sanity_results(test_step, status):
    with open(sanity_results_file, "a") as f:
	    f.write(str(test_step) + " " + str(status) + "\n")
