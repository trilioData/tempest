#!/usr/bin/python
# -*- coding: utf-8 -*-
import smtplib


fromaddr = 'shyam.biradar@afourtech.com'
toaddrs  = 'shyam.biradar@triliodata.com'

result_table = """ <table style="width:100%" border="1">
  <tr>
    <b><th>TestName</th>
    <th>Result</th> </b>
  </tr>
"""

test_result_file = "test_results"
with open(test_result_file, "r") as f:
    for line in f:
        row=line.split()
        if (row[1] == "FAILED") :
            text_color = "red"
        else :
            text_color = "green"
        result_table+="""<tr>
          <td><font color="%s">%s</font></td>
          <td><font color="%s">%s</font></td>
          </tr> """ % (text_color, row[0], text_color, row[1])
result_table+="""</table>"""

print result_table

message = """From: Tempest <shyam.biradar@afourtech.com>
To: Shyam <shyam.biradar@triliodata.com>
MIME-Version: 1.0
Content-type: text/html
Subject: Tempest Testrun Report - 2.1.110

<h1>Test Results:</h1>
<dev> %s </dev>

""" % result_table

username = 'shyam.biradar@afourtech.com'
password = 'ink!1234'

try:
  server = smtplib.SMTP('smtp.gmail.com:587')
  server.ehlo()
  server.starttls()
  server.login(username,password)
  server.sendmail(fromaddr, toaddrs, message)
  server.quit()
  print "Sent Email"
except smtplib.SMTPException:
   print "Error: unable to send email"
