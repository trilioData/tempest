from mysql.connector import errorcode
import mysql.connector
from tempest import tvaultconf
import paramiko

def get_db_credentials(hostip=tvaultconf.tvault_ip,user=tvaultconf.tvault_dbusername,
			pwd=tvaultconf.tvault_password):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.load_system_host_keys()
    ssh.connect(hostname=hostip, username=user, password=pwd)
    command = "cat /etc/workloadmgr/workloadmgr.conf | grep 'sql_connection' | cut -d '/' -f 3 | cut -d '@' -f 1"
    stdin, stdout, stderr = ssh.exec_command(command)
    credentials = stdout.read()
    return credentials


def dbHandler():
    try:
        cred = (str(get_db_credentials(hostip=tvaultconf.tvault_ip)).split("\n"))[0].split(":")
        conn = mysql.connector.connect(user=cred[0],password=cred[1],
                                       host=tvaultconf.tvault_ip,database=tvaultconf.tvault_dbname)
        print conn
        return conn
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)


def closeDbConnection():
    try:
        conn = dbHandler()
        conn.close()
    except Exception as e:
        print (str(e))
