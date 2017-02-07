from tempest import tvaultconf

workload_list = "workloadmgr workload-list | grep available | wc -l"
snapshot_list = "workloadmgr snapshot-list | grep available | wc -l"
restore_list = "workloadmgr restore-list | grep available | wc -l"

workload_create = "workloadmgr workload-create --workload-type-id "+tvaultconf.workload_type_id+\
                  " --display-name "+tvaultconf.workload_name+\
                  " --source-platform "+tvaultconf.source_platform
snapshot_create = "workloadmgr workload-snapshot " + " --full --display-name " +tvaultconf.snapshot_name + " "
snapshot_delete = "workloadmgr snapshot-delete "
workload_delete = "workloadmgr workload-delete "
restore_delete = "workloadmgr restore-delete "
delete_vm = "nova delete "
oneclick_restore = "workloadmgr snapshot-oneclick-restore --display-name " +tvaultconf.restore_name
selective_restore = "workloadmgr snapshot-selective-restore --display-name " +tvaultconf.selective_restore_name+ " --filename " +tvaultconf.restore_filename
list_vm = "nova list | awk -F '|' '{print $2}' | grep -v ID"
workload_modify = "workloadmgr workload-modify --instance instance-id="
workload_unlock = "workloadmgr workload-unlock "
incr_snapshot_create = "workloadmgr workload-snapshot " + " --display-name " +tvaultconf.snapshot_name + " "
workload_type_list = "workloadmgr workload-type-list | grep '[a-z0-9]-[a-z0-9]' | wc -l"
workload_type_show = "workloadmgr workload-type-show " + str(tvaultconf.workload_type_id)
workload_show = "workloadmgr workload-show "
