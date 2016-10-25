import db_handler


def get_workload_count(workload_name):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_count = ("select count(*) from workloads where display_name='"+workload_name+"' and status=\"available\"")
        cursor.execute(get_workload_count)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print (str(e))
    finally:
        cursor.close()
        conn.close()

def get_workload_id(workload_name):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_id = ("select id from workloads where display_name='"+workload_name+"' and status=\"available\"")
        cursor.execute(get_workload_id)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print (str(e))
    finally:
        cursor.close()
        conn.close()


def get_deleted_workload(workload_name):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_deleted_workload = ("select status from workloads where display_name='"+workload_name+"' order by updated_at desc limit 1")
        cursor.execute(get_deleted_workload)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print (str(e))
    finally:
        cursor.close()
        conn.close()


def get_available_snapshots(snapshot_name):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_available_snapshots = ("select count(*) from snapshots where display_name='"+snapshot_name+"' and deleted=0 order by created_at desc limit 1")
        cursor.execute(get_available_snapshots)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print (str(e))
    finally:
        cursor.close()
        conn.close()

def get_available_workloads():
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_available_workloads = ("select count(*) from workloads where status=\"available\"")
        cursor.execute(get_available_workloads)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print (str(e))
    finally:
        cursor.close()
        conn.close()

def get_available_restores():
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_available_restores = ("select count(*) from restores where status=\"available\"")
        cursor.execute(get_available_restores)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print (str(e))
    finally:
        cursor.close()
        conn.close()

def get_workload_snapshot_status(snapshot_name,snapshot_type):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_snapshot = ("select status from snapshots where display_name='"+snapshot_name+"' and snapshot_type='"+snapshot_type+"' order by created_at desc limit 1")
        cursor.execute(get_workload_snapshot)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print (str(e))
    finally:
        cursor.close()
        conn.close()


def get_workload_snapshot_delete_status(snapshot_name,snapshot_type):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_snapshot_delete_status = ("select deleted from snapshots where display_name='"+snapshot_name+"' and snapshot_type='"+snapshot_type+"' order by deleted_at desc limit 1")
        cursor.execute(get_workload_snapshot_delete_status)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print (str(e))
    finally:
        cursor.close()
        conn.close()


def get_workload_vmid(workload_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_vmid = ("select vm_id from workload_vms where workload_id='"+workload_id+"'")
        cursor.execute(get_workload_vmid)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print (str(e))
    finally:
        cursor.close()
        conn.close()


def get_workload_snapshot_id(workload_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_vmid = ("select id from snapshots where workload_id='"+workload_id+"' and status=\"available\" order by updated_at desc limit 1")
        cursor.execute(get_workload_vmid)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print (str(e))
    finally:
        cursor.close()
        conn.close()


def get_snapshot_restore_status(restore_name,snapshot_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_snapshot_restore_status = ("select status from restores where display_name='"+restore_name+"' and snapshot_id='"+snapshot_id+"' order by created_at desc limit 1")
        cursor.execute(get_snapshot_restore_status)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print (str(e))
    finally:
        cursor.close()
        conn.close()


def get_workload_display_name(workload_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_display_name = ("select display_name from workloads where id='"+workload_id+"'")
        cursor.execute(get_workload_display_name)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print (str(e))
    finally:
        cursor.close()
        conn.close()


def get_workload_display_description(workload_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_display_description = ("select display_description from workloads where id='"+workload_id+"'")
        cursor.execute(get_workload_display_description)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print (str(e))
    finally:
        cursor.close()
        conn.close()


def get_vmids():
    try:
        vmlist = []
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_vmids = ("select vm_id from workload_vms where status=\"available\"")
        cursor.execute(get_vmids)
        rows = cursor.fetchall()
        for row in rows:
            vmlist.append(str(row[0]))
        return vmlist
    except Exception as e:
        print (str(e))
    finally:
        cursor.close()
        conn.close()


def get_workload_status(workload_name):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_snapshot = ("select status from workloads where display_name='"+workload_name+"' order by created_at desc limit 1")
        cursor.execute(get_workload_snapshot)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print (str(e))
    finally:
        cursor.close()
        conn.close()
