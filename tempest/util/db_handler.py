from mysql.connector import errorcode
import mysql.connector
from tempest import tvaultconf

def dbHandler():
    try:
        if tvaultconf.wlm_dbport:
            conn = mysql.connector.connect(user=tvaultconf.wlm_dbusername,
                                       password=tvaultconf.wlm_dbpasswd,
                                       host=tvaultconf.wlm_dbhost,
                                       port=tvaultconf.wlm_dbport,
                                       database=tvaultconf.tvault_dbname)
        else:
            conn = mysql.connector.connect(user=tvaultconf.wlm_dbusername,
                                       password=tvaultconf.wlm_dbpasswd,
                                       host=tvaultconf.wlm_dbhost,
                                       database=tvaultconf.tvault_dbname)
        print(conn)
        return conn
    except mysql.connector.Error as err:
        print(err)
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
        print(str(e))
