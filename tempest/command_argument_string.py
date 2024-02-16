from tempest import tvaultconf

#Workload commands
workload_list = "workloadmgr --insecure workload-list | grep available | wc -l"
workload_create = "workloadmgr --insecure workload-create "\
                  " --display-name "+tvaultconf.workload_name+\
                  " --source-platform "+tvaultconf.source_platform
workload_create_with_encryption = "workloadmgr --insecure workload-create "\
                  " --display-name "+tvaultconf.workload_name+ \
                  " --encryption True" + \
                  " --source-platform "+tvaultconf.source_platform
workload_delete = "workloadmgr --insecure workload-delete "
workload_delete_db = "workloadmgr --insecure workload-delete --database_only "
workload_modify = "workloadmgr --insecure workload-modify "
workload_unlock = "workloadmgr --insecure workload-unlock "
workload_show = "workloadmgr --insecure workload-show "
workload_import = "workloadmgr --insecure workload-importworkloads"
workload_setting_create = "workloadmgr --insecure setting-create "
workload_setting_show = "workloadmgr --insecure setting-show "
workload_setting_delete = " workloadmgr --insecure setting-delete "
workload_setting_update = "workloadmgr --insecure setting-update "
workload_setting_list = "workloadmgr --insecure setting-list "
workload_get_orphaned_workloads_list = "workloadmgr --insecure workload-get-orphaned-workloads-list --generate_yaml True"

#Trust commands
workload_scheduler_trust_check = "workloadmgr --insecure scheduler-trust-validate "
trust_create = "workloadmgr --insecure trust-create -f json --is_cloud_trust False "
trust_list = "workloadmgr --insecure trust-list -f json"
trust_show = "workloadmgr --insecure trust-show -f json "
trust_delete = "workloadmgr --insecure trust-delete "

get_storage_usage = "workloadmgr --insecure workload-get-storage-usage"
get_tenant_usage = "workloadmgr --insecure get-tenants-usage"
get_import_workloads_list = "workloadmgr --insecure workload-get-importworkloads-list" 
workload_disable_global_job_scheduler = "workloadmgr --insecure disable-global-job-scheduler"
workload_enable_global_job_scheduler = "workloadmgr --insecure enable-global-job-scheduler"
get_nodes  = "workloadmgr --insecure workload-get-nodes" 
get_auditlog = "workloadmgr --insecure workload-get-auditlog"
service_disable = "workloadmgr --insecure workload-service-disable --reason '" + tvaultconf.wlm_disable_reason + "' "
service_enable = "workloadmgr --insecure workload-service-enable "

#Snapshot commands
snapshot_list = "workloadmgr --insecure snapshot-list | grep available | wc -l"
snapshot_create = "workloadmgr --insecure workload-snapshot " + " --full --display-name " +tvaultconf.snapshot_name + " "
snapshot_delete = "workloadmgr --insecure snapshot-delete "
incr_snapshot_create = "workloadmgr --insecure workload-snapshot " + " --display-name " +tvaultconf.snapshot_name + " "
snapshot_cancel = "workloadmgr --insecure snapshot-cancel "
snapshot_reset = "workloadmgr --insecure snapshot-reset --snapshot_id "

#Snapshot mount commands
snapshot_mount = "workloadmgr --insecure snapshot-mount "
snapshot_dismount = "workloadmgr --insecure snapshot-dismount "
snapshot_mounted_list = "workloadmgr --insecure snapshot-mounted-list "
snapshot_show = "workloadmgr --insecure --insecure snapshot-show --output metadata "

#Restore commands
restore_list = "workloadmgr --insecure restore-list | grep available | wc -l"
restore_delete = "workloadmgr --insecure restore-delete "
oneclick_restore = "workloadmgr --insecure snapshot-oneclick-restore --display-name " +tvaultconf.restore_name
selective_restore = "workloadmgr --insecure snapshot-selective-restore --display-name " +tvaultconf.selective_restore_name+ " --filename " +tvaultconf.restore_filename
restore_show = "workloadmgr --insecure restore-show "
inplace_restore = "workloadmgr --insecure snapshot-inplace-restore --display-name test_name_inplace --display-description test_description_inplace  --filename "
restore_cancel = "workloadmgr --insecure restore-cancel "
restore_security_groups = "workloadmgr --insecure restore-security-groups "
network_restore = "workloadmgr --insecure restore-network-topology "

#Restore commands with blank names.
oneclick_restore_with_blank_name = "workloadmgr --insecure --insecure snapshot-oneclick-restore --display-name \" \" --display-description \" \" "
inplace_restore_with_blank_name = "workloadmgr --insecure --insecure snapshot-inplace-restore --display-name \" \" --display-description \" \" --filename "
selective_restore_with_blank_name = "workloadmgr --insecure --insecure snapshot-selective-restore --display-name \" \" --display-description \" \" --filename "

#openstack secret commands
openstack_create_secret_with_empty_payload = "openstack secret store -p \"\" -f json "

#Nova commands
delete_vm = "nova delete "
list_vm = "nova list | awk -F '|' '{print $2}' | grep -v ID"

#License commands
license_create = "workloadmgr --insecure license-create "
license_check = "workloadmgr --insecure license-check"
license_list = "workloadmgr --insecure license-list"

#Workload policy commands
policy_create = "workloadmgr --insecure policy-create --policy-fields "
policy_update = "workloadmgr --insecure policy-update --policy-fields "
policy_assign = "workloadmgr --insecure policy-assign --add_project "
policy_delete = "workloadmgr --insecure policy-delete "
list_assigned_policies = "workloadmgr --insecure list-assigned-policies "

#Quota commands
quota_type_list_count = "workloadmgr --insecure project-quota-type-list | grep '[a-z0-9]-[a-z0-9]' | wc -l"
quota_type_list = "workloadmgr --insecure project-quota-type-list -f json "
quota_create = "workloadmgr --insecure project-allowed-quota-create "
quota_update = "workloadmgr --insecure project-allowed-quota-update "
quota_list = "workloadmgr --insecure project-allowed-quota-list -f json "
quota_show = "workloadmgr --insecure project-allowed-quota-show -f value "
quota_delete = "workloadmgr --insecure project-allowed-quota-delete "

#RBAC commands
rbac_create_secgroup = "openstack network rbac create --target-project "

#OpenStack WLM CLI Commands
os_workload_list = "openstack workload list"


#OpenStack CLI Commands
os_server_list = "openstack server list"
