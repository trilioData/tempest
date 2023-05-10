from tempest import tvaultconf

#Workload commands
workload_list = "workloadmgr workload-list | grep available | wc -l"
workload_create = "workloadmgr workload-create "\
                  " --display-name "+tvaultconf.workload_name+\
                  " --source-platform "+tvaultconf.source_platform
workload_create_with_encryption = "workloadmgr workload-create "\
                  " --display-name "+tvaultconf.workload_name+ \
                  " --encryption True" + \
                  " --source-platform "+tvaultconf.source_platform
workload_delete = "workloadmgr workload-delete "
workload_delete_db = "workloadmgr workload-delete --database_only "
workload_modify = "workloadmgr workload-modify "
workload_unlock = "workloadmgr workload-unlock "
workload_show = "workloadmgr workload-show "
workload_import = "workloadmgr workload-importworkloads"
workload_setting_create = "workloadmgr setting-create "
workload_setting_show = "workloadmgr setting-show "
workload_setting_delete = " workloadmgr setting-delete "
workload_setting_update = "workloadmgr setting-update "
workload_setting_list = "workloadmgr setting-list "
workload_get_orphaned_workloads_list = "workloadmgr workload-get-orphaned-workloads-list --generate_yaml True"

#Trust commands
workload_scheduler_trust_check = "workloadmgr scheduler-trust-validate "
trust_create = "workloadmgr trust-create -f json --is_cloud_trust False "
trust_list = "workloadmgr trust-list -f json"
trust_show = "workloadmgr trust-show -f json "
trust_delete = "workloadmgr trust-delete "

get_storage_usage = "workloadmgr workload-get-storage-usage" 
get_import_workloads_list = "workloadmgr workload-get-importworkloads-list" 
workload_disable_global_job_scheduler = "workloadmgr disable-global-job-scheduler"
workload_enable_global_job_scheduler = "workloadmgr enable-global-job-scheduler"
get_nodes  = "workloadmgr workload-get-nodes" 
get_auditlog = "workloadmgr workload-get-auditlog"
service_disable = "workloadmgr workload-service-disable --reason '" + tvaultconf.wlm_disable_reason + "' "
service_enable = "workloadmgr workload-service-enable "

#Snapshot commands
snapshot_list = "workloadmgr snapshot-list | grep available | wc -l"
snapshot_create = "workloadmgr workload-snapshot " + " --full --display-name " +tvaultconf.snapshot_name + " "
snapshot_delete = "workloadmgr snapshot-delete "
incr_snapshot_create = "workloadmgr workload-snapshot " + " --display-name " +tvaultconf.snapshot_name + " "
snapshot_cancel = "workloadmgr snapshot-cancel "

#Snapshot mount commands
snapshot_mount = "workloadmgr snapshot-mount "
snapshot_dismount = "workloadmgr snapshot-dismount "
snapshot_mounted_list = "workloadmgr snapshot-mounted-list "
snapshot_show = "workloadmgr --insecure snapshot-show --output metadata "

#Restore commands
restore_list = "workloadmgr restore-list | grep available | wc -l"
restore_delete = "workloadmgr restore-delete "
oneclick_restore = "workloadmgr snapshot-oneclick-restore --display-name " +tvaultconf.restore_name
selective_restore = "workloadmgr snapshot-selective-restore --display-name " +tvaultconf.selective_restore_name+ " --filename " +tvaultconf.restore_filename
restore_show = "workloadmgr restore-show "
inplace_restore = "workloadmgr snapshot-inplace-restore --display-name test_name_inplace --display-description test_description_inplace  --filename "
restore_cancel = "workloadmgr restore-cancel "
restore_security_groups = "workloadmgr restore-security-groups "
network_restore = "workloadmgr restore-network-topology "

#Restore commands with blank names.
oneclick_restore_with_blank_name = "workloadmgr --insecure snapshot-oneclick-restore --display-name \" \" --display-description \" \" "
inplace_restore_with_blank_name = "workloadmgr --insecure snapshot-inplace-restore --display-name \" \" --display-description \" \" --filename "
selective_restore_with_blank_name = "workloadmgr --insecure snapshot-selective-restore --display-name \" \" --display-description \" \" --filename "

#openstack secret commands
openstack_create_secret_with_empty_payload = "openstack secret store -p \"\" -f json "

#Nova commands
delete_vm = "nova delete "
list_vm = "nova list | awk -F '|' '{print $2}' | grep -v ID"

#License commands
license_create = "workloadmgr license-create "
license_check = "workloadmgr license-check"
license_list = "workloadmgr license-list"

#Workload policy commands
policy_create = "workloadmgr policy-create --policy-fields "
policy_update = "workloadmgr policy-update --policy-fields "
policy_assign = "workloadmgr policy-assign --add_project "
policy_delete = "workloadmgr policy-delete "
list_assigned_policies = "workloadmgr list-assigned-policies "

#Quota commands
quota_type_list_count = "workloadmgr project-quota-type-list | grep '[a-z0-9]-[a-z0-9]' | wc -l"
quota_type_list = "workloadmgr project-quota-type-list -f json "
quota_create = "workloadmgr project-allowed-quota-create "
quota_update = "workloadmgr project-allowed-quota-update "
quota_list = "workloadmgr project-allowed-quota-list -f json "
quota_show = "workloadmgr project-allowed-quota-show -f value "
quota_delete = "workloadmgr project-allowed-quota-delete "

#RBAC commands
rbac_create_secgroup = "openstack network rbac create --target-project "
