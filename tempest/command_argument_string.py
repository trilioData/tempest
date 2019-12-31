from tempest import tvaultconf

#Workload commands
workload_list = "workloadmgr workload-list | grep available | wc -l"
workload_create = "workloadmgr workload-create --workload-type-id "+tvaultconf.workload_type_id+\
                  " --display-name "+tvaultconf.workload_name+\
                  " --source-platform "+tvaultconf.source_platform
workload_delete = "workloadmgr workload-delete "
workload_modify = "workloadmgr workload-modify "
workload_unlock = "workloadmgr workload-unlock "
workload_type_list = "workloadmgr workload-type-list | grep '[a-z0-9]-[a-z0-9]' | wc -l"
workload_type_show = "workloadmgr workload-type-show " + str(tvaultconf.workload_type_id)
workload_show = "workloadmgr workload-show "
workload_import = "workloadmgr workload-importworkloads"

get_storage_usage = "workloadmgr workload-get-storage-usage" 
get_import_workloads_list = "workloadmgr workload-get-importworkloads-list" 
workload_disable_global_job_scheduler = "workloadmgr disable-global-job-scheduler"
workload_enable_global_job_scheduler = "workloadmgr enable-global-job-scheduler"
get_nodes  = "workloadmgr workload-get-nodes" 
get_auditlog = "workloadmgr workload-get-auditlog"


#Snapshot commands
snapshot_list = "workloadmgr snapshot-list | grep available | wc -l"
snapshot_create = "workloadmgr workload-snapshot " + " --full --display-name " +tvaultconf.snapshot_name + " "
snapshot_delete = "workloadmgr snapshot-delete "
incr_snapshot_create = "workloadmgr workload-snapshot " + " --display-name " +tvaultconf.snapshot_name + " "
snapshot_cancel = "workloadmgr snapshot-cancel "

#Restore commands
restore_list = "workloadmgr restore-list | grep available | wc -l"
restore_delete = "workloadmgr restore-delete "
oneclick_restore = "workloadmgr snapshot-oneclick-restore --display-name " +tvaultconf.restore_name
selective_restore = "workloadmgr snapshot-selective-restore --display-name " +tvaultconf.selective_restore_name+ " --filename " +tvaultconf.restore_filename
restore_show = "workloadmgr restore-show "
inplace_restore = "workloadmgr snapshot-inplace-restore --display-name test_name_inplace --display-description test_description_inplace  --filename "
restore_cancel = "workloadmgr restore-cancel "

#Nova commands
delete_vm = "nova delete "
list_vm = "nova list | awk -F '|' '{print $2}' | grep -v ID"

#License commands
license_create = "workloadmgr license-create "
license_check = "workloadmgr license-check"
license_list = "workloadmgr license-list"

#Config backup commands
config_workload_configure = "workloadmgr config-workload-configure"
config_workload_show = "workloadmgr config-workload-show"
config_backup = "workloadmgr config-backup"
config_backup_show = "workloadmgr config-backup-show"
config_backup_delete = "workloadmgr config-backup-delete"

#Workload policy commands
policy_create = "workloadmgr policy-create --policy-fields "
policy_update = "workloadmgr policy-update --policy-fields "
policy_assign = "workloadmgr policy-assign --add_project "
policy_delete = "workloadmgr policy-delete "
