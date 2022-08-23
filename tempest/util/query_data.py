from tempest.util import db_handler
from oslo_log import log as logging
from tempest import config
LOG = logging.getLogger(__name__)
CONF = config.CONF


def get_workload_count(workload_name):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_count = ("select count(*) from workloads where display_name='" +
                              workload_name + "' and status=\"available\"")
        cursor.execute(get_workload_count)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_workload_id(workload_name):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_id = ("select id from workloads where display_name='" +
                           workload_name + "' and status=\"available\" order by created_at desc limit 1")
        cursor.execute(get_workload_id)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_workload_id_in_creation(workload_name):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_id = ("select id from workloads where display_name='" +
                           workload_name + "' and status <> 'deleted' order by created_at desc limit 1")
        cursor.execute(get_workload_id)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()

def get_deleted_workload(workload_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_deleted_workload = ("select status from workloads where id='" +
                                str(workload_id) + "' order by updated_at desc limit 1")
        cursor.execute(get_deleted_workload)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_available_snapshots_for_workload(snapshot_name, workload_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_available_snapshots = ("select count(*) from snapshots where display_name='" + snapshot_name +
                                   "' and workload_id='" + str(workload_id) + "' and deleted=0 order by created_at desc limit 1")
        cursor.execute(get_available_snapshots)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_available_snapshots(project_id=""):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        if project_id:
            get_available_snapshots = ("select count(*) from snapshots where "
                                       "deleted=0 and status = 'available' and "
                                       "project_id = '%s'" % project_id )
        else:
            get_available_snapshots = ("select count(*) from snapshots where "
                                       "deleted=0 and status = 'available' ")
        cursor.execute(get_available_snapshots)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_available_workloads(project_id=""):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        if project_id:
            get_available_workloads = (
                "select count(*) from workloads where status=\"available\" "
                "and project_id=\"%s\"" % project_id)
        else:
            get_available_workloads = (
            "select count(*) from workloads where status=\"available\"")
        cursor.execute(get_available_workloads)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_available_restores(project_id=""):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        if project_id:
            get_available_restores = ('select count(*) from restores where '
                                      'status="available" and project_id="%s"'
                                      % project_id)
        else:
            get_available_restores = (
            'select count(*) from restores where status="available"')
        cursor.execute(get_available_restores)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_workload_snapshot_status(snapshot_name, snapshot_type, snapshot_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_snapshot = ("select status from snapshots where display_name='" + snapshot_name +
                                 "' and snapshot_type='" + snapshot_type + "' and id='" + str(snapshot_id) + "' order by created_at desc limit 1")
        cursor.execute(get_workload_snapshot)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_workload_snapshot_delete_status(snapshot_name, snapshot_type, snapshot_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_snapshot_delete_status = ("select deleted from snapshots where display_name='" + snapshot_name +
                                               "' and snapshot_type='" + snapshot_type + "' and id='" + str(snapshot_id) + "' order by deleted_at desc limit 1")
        cursor.execute(get_workload_snapshot_delete_status)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_workload_vmid(workload_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_vmid = (
            "select vm_id from workload_vms where workload_id='" + workload_id + "'")
        cursor.execute(get_workload_vmid)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_workload_snapshot_id(workload_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_vmid = ("select id from snapshots where workload_id='" +
                             workload_id + "' and status=\"available\" order by updated_at desc limit 1")
        cursor.execute(get_workload_vmid)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_inprogress_snapshot_id(workload_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_vmid = ("select id from snapshots where workload_id='" +
                             workload_id + "' and status<>'available' order by updated_at desc limit 1")
        cursor.execute(get_workload_vmid)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_snapshot_restore_status(restore_name, snapshot_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_snapshot_restore_status = ("select status from restores where display_name='" +
                                       restore_name + "' and snapshot_id='" + snapshot_id + "' order by created_at desc limit 1")
        cursor.execute(get_snapshot_restore_status)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_workload_display_name(workload_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_display_name = (
            "select display_name from workloads where id='" + workload_id + "'")
        cursor.execute(get_workload_display_name)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_workload_display_description(workload_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_display_description = (
            "select display_description from workloads where id='" + workload_id + "'")
        cursor.execute(get_workload_display_description)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_vmids():
    try:
        vmlist = []
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_vmids = (
            "select vm_id from workload_vms where status=\"available\"")
        cursor.execute(get_vmids)
        rows = cursor.fetchall()
        for row in rows:
            vmlist.append(str(row[0]))
        return vmlist
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_workload_status(workload_name):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_snapshot = ("select status from workloads where display_name='" +
                                 workload_name + "' order by created_at desc limit 1")
        cursor.execute(get_workload_snapshot)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_snapshot_restore_delete_status(restore_name, restore_type):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_snapshot_restore_delete_status = ("select deleted from restores where display_name='" +
                                              restore_name + "' and restore_type='" + restore_type + "' order by deleted_at desc limit 1")
        cursor.execute(get_snapshot_restore_delete_status)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_snapshot_restore_id(snapshot_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_snapshot_restore_id = ("select id from restores where snapshot_id='" +
                                   snapshot_id + "' order by created_at desc limit 1")
        cursor.execute(get_snapshot_restore_id)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_restored_vmids(restore_id):
    try:
        vm_ids = []
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_restored_vmid = (
            "select vm_id from restored_vms where restore_id='" + restore_id + "'")
        cursor.execute(get_restored_vmid)
        rows = cursor.fetchall()
        for row in rows:
            vm_ids.append(row[0])
        return vm_ids
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_available_vms_of_workload(workload_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_count = ("select count(*) from workload_vms where workload_id='" +
                     str(workload_id) + "' and status <> 'deleted';")
        cursor.execute(get_count)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_workload_status_by_id(workload_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_snapshot = ("select status from workloads where id='" +
                                 workload_id + "' order by created_at desc limit 1")
        cursor.execute(get_workload_snapshot)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        LOG.error(str(e))
    finally:
        cursor.close()
        conn.close()


def get_workload_schedule(workload_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_schedule = ("select jobschedule from workloads where id='" +
                                 workload_id + "' order by created_at desc limit 1")
        cursor.execute(get_workload_schedule)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        LOG.error(str(e))
    finally:
        cursor.close()
        conn.close()


def get_available_workload_types():
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_types = (
            "select count(*) from workload_types where deleted <> 1")
        cursor.execute(get_workload_types)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        LOG.error(str(e))
    finally:
        cursor.close()
        conn.close()


def get_workload_type_data(workload_type_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_types = (
            "select * from workload_types where deleted <> 1 and ID='" + str(workload_type_id) + "'")
        cursor.execute(get_workload_types)
        rows = cursor.fetchall()
        for row in rows:
            return row
    except Exception as e:
        LOG.error(str(e))
    finally:
        cursor.close()
        conn.close()


def get_workload_vmids(workload_id):
    try:
        vm_ids = []
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_workload_vmid = (
            "select vm_id from workload_vms where workload_id='" + workload_id + "'")
        cursor.execute(get_workload_vmid)
        rows = cursor.fetchall()
        for row in rows:
            vm_ids.append(row[0])
        return vm_ids
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_config_backup_id():
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_config_backup_id = (
            "select id from config_backups order by created_at desc limit 1")
        cursor.execute(get_config_backup_id)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_config_workload_id():
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_config_backup_id = ("select id from config_workloads;")
        cursor.execute(get_config_backup_id)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_available_project_quota_types():
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_quota_types = (
            "select count(*) from project_quota_types where deleted <> 1")
        cursor.execute(get_quota_types)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        LOG.error(str(e))
    finally:
        cursor.close()
        conn.close()


def get_quota_id(quota_type_id, project_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        cmd = "select id from allowed_quota where quota_type_id = '" + \
                    quota_type_id + "' and project_id = '" + \
                    project_id + "' and deleted <> 1"
        cursor.execute(cmd)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        LOG.error(str(e))
    finally:
        cursor.close()
        conn.close()


def get_quota_details(quota_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        cmd = "select allowed_value, high_watermark, a.id, a.project_id, "\
              "a.quota_type_id, b.display_name, a.version from " \
              "allowed_quota as a, project_quota_types b where a.deleted <> 1"\
              " and a.quota_type_id=b.id and a.id='" + quota_id + "'"
        cursor.execute(cmd)
        rows = cursor.fetchall()
        for row in rows:
            return row
    except Exception as e:
        LOG.error(str(e))
    finally:
        cursor.close()
        conn.close()


def get_available_quotas_count(project_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        cmd = "select count(*) from allowed_quota where deleted <> 1 " \
              "and project_id='" + project_id + "'"
        cursor.execute(cmd)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        LOG.error(str(e))
    finally:
        cursor.close()
        conn.close()


def get_trust_list(project_id, user_id):
    try:
        trusts = []
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        cmd = "select name from settings where category='identity' and " +\
                "project_id='" + project_id + "' and user_id='" + user_id + "'"
        cursor.execute(cmd)
        rows = cursor.fetchall()
        for row in rows:
            trusts.append(row[0])
        return trusts
    except Exception as e:
        LOG.error(str(e))
    finally:
        cursor.close()
        conn.close()


def get_trust_details(trust_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        cmd = "select version, user_id, project_id, name, value, description"+\
                ", status from settings where category='identity' and " +\
                "name='" + trust_id + "'"
        cursor.execute(cmd)
        rows = cursor.fetchall()
        return rows[0]
    except Exception as e:
        LOG.error(str(e))
    finally:
        cursor.close()
        conn.close()


def get_db_rows_count(table_name, column_name, column_value):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_count = ("select count(*) from " + table_name + " where " + column_name + "='" + column_value + "'")
        cursor.execute(get_count)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_workload_vm_data(workload_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_count = (
                    "select count(*) from workload_vm_metadata inner join workload_vms on workload_vm_metadata.workload_vm_id=workload_vms.id where workload_vms.workload_id='" + workload_id + "'")
        cursor.execute(get_count)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_snapshot_vm_data(snapshot_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_count = (
                    "select count(*) from snapshot_vm_metadata inner join snapshot_vms on snapshot_vm_metadata.snapshot_vm_id=snapshot_vms.id where snapshot_vms.snapshot_id='" + snapshot_id + "'")
        cursor.execute(get_count)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_vm_disk_resource_snaps(snapshot_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_count = (
                    "select count(*) from vm_disk_resource_snaps inner join snapshot_vm_resources on vm_disk_resource_snaps.snapshot_vm_resource_id=snapshot_vm_resources.id where snapshot_vm_resources.snapshot_id='" + snapshot_id + "'")
        cursor.execute(get_count)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_vm_disk_resource_snaps_metadata(snapshot_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_count = (
                    "select count(*) from vm_disk_resource_snap_metadata inner join vm_disk_resource_snaps on vm_disk_resource_snap_metadata.vm_disk_resource_snap_id=vm_disk_resource_snaps.id inner join  snapshot_vm_resources on vm_disk_resource_snaps.snapshot_vm_resource_id=snapshot_vm_resources.id where snapshot_vm_resources.snapshot_id='" + snapshot_id + "'")
        cursor.execute(get_count)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_vm_network_resource_snaps(snapshot_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_count = (
                    "select count(*) from vm_network_resource_snaps inner join snapshot_vm_resources on vm_network_resource_snaps.vm_network_resource_snap_id=snapshot_vm_resources.id where snapshot_vm_resources.snapshot_id='" + snapshot_id + "'")
        cursor.execute(get_count)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_vm_network_resource_snaps_metadata(snapshot_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_count = (
                    "select count(*) from vm_network_resource_snap_metadata inner join vm_network_resource_snaps on vm_network_resource_snap_metadata.vm_network_resource_snap_id=vm_network_resource_snaps.vm_network_resource_snap_id inner join snapshot_vm_resources on vm_network_resource_snaps.vm_network_resource_snap_id=snapshot_vm_resources.id where snapshot_vm_resources.snapshot_id='" + snapshot_id + "'")
        cursor.execute(get_count)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_snap_network_resource_metadata(snapshot_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_count = (
                    "select count(*) from snap_network_resource_metadata inner join snap_network_resources on snap_network_resource_metadata.snap_network_resource_id=snap_network_resources.id where snap_network_resources.snapshot_id='" + snapshot_id + "'")
        cursor.execute(get_count)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_restored_vm_metadata(restore_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_count = (
                    "select count(*) from restored_vm_metadata inner join restored_vms on restored_vm_metadata.restored_vm_id=restored_vms.id where restored_vms.restore_id='" + restore_id + "'")
        cursor.execute(get_count)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()


def get_restored_vm_resource_metadata(restore_id):
    try:
        conn = db_handler.dbHandler()
        cursor = conn.cursor()
        get_count = (
                    "select count(*) from restored_vm_resource_metadata inner join restored_vm_resources on restored_vm_resource_metadata.restored_vm_resource_id=restored_vm_resources.id where restored_vm_resources.restore_id='" + restore_id + "'")
        cursor.execute(get_count)
        rows = cursor.fetchall()
        for row in rows:
            return row[0]
    except Exception as e:
        print(str(e))
    finally:
        cursor.close()
        conn.close()
