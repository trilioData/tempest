def setup_report():
    with open("/root/tempest/Report/results.html", "a") as f:
        f.seek(0)
        f.truncate()

    head = """<table style="width:100%" border="1">
            <tr>
                <b>
                    <th>TestName</th>
                    <th>Result</th>
                </b>
            </tr>
            """
    with open("/root/tempest/Report/results.html", "w+") as f:
            f.write(head)

def add_test_step(teststep, status):
    if status:
        color = "green"
        status_string = "PASS"
    else:
        color = "red"
        status_string= "FAIL"
    message = """<tr>
                    <td style="text-align:center">
			<font color={0}>{2}</font>
                    <td style="text-align:center">
                	<font color={0}>{1}</font>
                """.format(color, status_string, teststep)
    with open("/root/tempest/Report/results.html", "a") as f:
        f.write(message)

def add_test_script(script):
    message = """
	<tr>
	    <b>
		<th colspan="2">{}</th>
            </b>
        </tr>
	""".format(script)
    with open("/root/tempest/Report/results.html", "a") as f:
        f.write(message)
setup_report()
