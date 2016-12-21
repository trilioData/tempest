#!/usr/bin/expect

set BUILD_NUMBER [lindex $argv 0]

pwd
spawn scp -r logs root@192.168.1.62:/var/lib/jenkins/jobs/Tvault_Complete_Suite/builds/$BUILD_NUMBER/htmlreports/HTML_Test_Report/

while {1} {
  expect {

    eof                          {break}
    "Are you sure you want to continue connecting"   {send "yes\r"}
    "password:"                  {send "Password1!\r"}
    "*\]"                        {send "exit\r"}
  }
}
wait

