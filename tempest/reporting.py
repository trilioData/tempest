test_results_file="Report/results.html"
sanity_results_file="test_results"

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

def add_test_step(teststep, status):
    if status == "PASS":
        color = "green"
    else:
        color = "red"
    message = """<tr>
                    <td> <font color={0}>{2}</font> </td>
                    <td> <font color={0}>{1}</font> </td>
		 </tr>
                """.format(color, status, teststep)
    with open(test_results_file, "a") as f:
        f.write(message)

def add_test_script(script):
    message = """
	<tr>
		<td colspan="2">{}</td>
        </tr>
	""".format(script)
    with open(test_results_file, "a") as f:
        f.write(message)

def end_report_table():
    with open(test_results_file, "a") as f:
        f.write("</table>")

def add_sanity_results(test_step, status):
    with open(sanity_results_file, "a") as f:
	f.write(str(test_step) + " " + str(status))
