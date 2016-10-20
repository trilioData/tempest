from mysql.connector import errorcode
import mysql.connector



def dbHandler():
    try:
        from config import configuration
        conn = mysql.connector.connect(user=configuration.tvault_username,password=configuration.tvault_password
                                       ,host=configuration.tvault_ip,database=configuration.tvault_dbname)
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
