#import apscheduler
#from apscheduler.schedulers.blocking import BlockingScheduler

#If you want to cleanup all test resources like vms, volumes, workloads then set
# following cleanup parameter value to True otherwise False
cleanup = True 

# pre requisite paramter
pre_req = True

#Test results for reporting
PASS = "PASS"
FAIL = "FAIL"

enabled_tests = ["Attached_Volume_Ceph"]

#Resources to use from file
#Please add your resources one on each line in files: tempest/tempest/vms_file, volumes_file, workloads_file
vms_from_file=False
volumes_from_file=False
workloads_from_file=False

#CLI configuration parameters
workload_name="clitest"
source_platform="openstack"
snapshot_name = "test-snapshot"
snapshot_type_full = "full"
restore_name = "test-oneclick-restore"
selective_restore_name = "test-selective-restore"
security_group_restore_name = "Security Groups Restore"
restore_filename = "/opt/restore.json"
vm_license_filename = "test_licenses/tvault_license_10VM.txt"
compute_license_filename = "test_licenses/tvault_license_10compute.txt"
invalid_license_filename = "test_licenses/tvault_license_invalid.txt"
expired_license_filename = "test_licenses/tvault_license_expired.txt"
triliovault_vol_snapshot_name = "TrilioVaultSnapshot"
workload_setting_name = "wl_setting_name"
workload_setting_value = "wl_setting_value"

workload_modify_name = "test2-new"
workload_modify_description = "test2-new-description"
restore_type = "restore"
global_job_scheduler=False

tvault_ip = []
tvault_version = "4.1.124"
tvault_username = "root"
tvault_dbname = "workloadmgr"
tvault_password = "sample-password"
wlm_dbusername = "workloadmgr"
wlm_dbpasswd = "sample-password"
wlm_dbhost = "192.168.6.17"
smtp_password = "sample-password"
smtp_password_pwdless = "sample-password"
trustee_role = "_member_"
test_role = "backup"

# Scheduler parameter

interval="1 hr"
interval_update = "7 hrs"
enabled='false'
retention_policy_type="Number of Snapshots to Keep"
retention_policy_type_update = "Number of days to retain Snapshots"
retention_policy_value="3"
retention_policy_value_update = "7"
schedule_report_file="scheduleReport.txt"
#sched=BlockingScheduler()
count=0
No_of_Backup=1

# Scheduler policy parameters
policy_name="policy2"
policy_name_update = "policy_update"
fullbackup_interval="8"
fullbackup_interval_update = "7"

# test parameters
key_pair_name  = "tempest_test_key_pair"
instance_username = "ubuntu"
snapshot_restore_name = "Tempest Test Restore"
restored_instance_flavor = 2
security_group_id = "baaae013-75d5-4821-806c-2cb259c95fb4"
security_group_name = "test-Security-Groups"
flavor_name = "test_flavor"
bootfromvol_vol_size = 4
volumes_parts = ["/dev/vdb", "/dev/vdc"]
mount_points = ["mount_data_b", "mount_data_c"]
user_frm_data = "/home/nchavan/tempest/tempest/frm_userdata.sh"
user_data_vm = "/home/nchavan/tempest/tempest/vm_userdata.sh"
curl_to_get_userdata = "http://169.254.169.254/2009-04-04/user-data"

#Email settings data
setting_data = {"smtp_default_recipient": "test@trilio.io",
                "smtp_default_sender": "test@trilio.io",
                "smtp_port": "587",
                "smtp_server_name": "smtp.gmail.com",
                "smtp_server_password": smtp_password,
                "smtp_server_username": "test@trilio.io",
                "smtp_timeout": "10" }
setting_data_pwdless = {"smtp_default_recipient": "test1@trilio.io",
                "smtp_default_sender": "test1@trilio.io",
                "smtp_port": "25",
                "smtp_server_name": "mail.triliodata.demo",
                "smtp_server_password": "",
                "smtp_server_username": "test1@trilio.io",
                "smtp_timeout": "10" }

enable_email_notification = {"smtp_email_enable" : 1}
disable_email_notification = {"smtp_email_enable" : 0}

#Glance image data
image_url = "https://cloud-images.ubuntu.com/focal/current/"
image_filename = "focal-server-cloudimg-amd64.img"
image_properties = {"hw_disk_busi": "scsi",
                    "hw_qemu_guest_agent": "yes",
                 #   "hw_scsi_model": "virtioscsi",
                    "hw_video_model": "qxl",
                    "hw_vif_model": "virtio",
                    "hw_vif_multiqueue_enabled": "true",
                    "os_distro": "ubuntu",
                    "os_require_quiesce": "true"}

#Parameter for multiple vm workloads etc
vm_count = 4

#WLM Quota parameters
workload_allowed_value = 1
workload_watermark_value = 1
vm_allowed_value = 1
vm_watermark_value = 1

#custom metadata for exclusion of bootdisk and cinder volume.
#metadata for the cinder volume exclusion
enable_cinder_volume_exclusion = {"exclude_from_backup": "True"}
#metadata for the bootdisk exclusion
enable_bootdisk_exclusion = {"exclude_boot_disk_from_backup": "True"}
disable_bootdisk_exclusion = {"exclude_boot_disk_from_backup": "False"}

#max retry count
max_retries = 20

#db cleanup validations tables
workload_tables = ["workloads", "workload_vms", "workload_vm_metadata", "scheduled_jobs", "snapshots"]
snapshot_tables = ["snapshots", "snapshot_metadata", "vm_recent_snapshot", "snapshot_vm_resources", "snapshot_vms", "snapshot_vm_metadata", "snapshot_vm_resources", "vm_disk_resource_snaps", "vm_disk_resource_snap_metadata", "vm_network_resource_snaps", "vm_network_resource_snap_metadata", "snap_network_resources", "snap_network_resource_metadata"]
restore_tables = ["restores", "restore_metadata", "restored_vms", "restored_vm_metadata", "restored_vm_resources", "restored_vm_resource_metadata"]
workload_policy_tables = ["workload_policy", "workload_policy_assignments", "workload_policy_metadata", "workload_policy_values"]
workload_policy_fields = ["fullbackup_interval", "interval", "retention_policy_type", "retention_policy_value"]

#error strings
wl_setting_cli_error_string = 'workloadmgr setting-create: error: the following arguments are required: '
wl_setting_update_cli_error_string = 'workloadmgr setting-update: error: argument --description: expected one argument'
wl_setting_list_cli_error_string = 'workloadmgr setting-list: error: argument --get_hidden: expected one argument'
wl_assigned_policy_error_string = "ERROR:workloadmgr:No recognized column names in ['id']. Recognized columns are ['ID', 'Name', 'Deleted', 'CreatedAt']"
wl_assigned_policy_no_projectid_error_string = 'workloadmgr list-assigned-policies: error: the following arguments are required: <project_id>'

#snapshot cancel cli error strings
error_cancel_snapshot_cli_without_any_options = "workloadmgr snapshot-cancel: error: the following arguments are required: <snapshot_id>"
error_cancel_snapshot_cli_with_invalid_workloadid_option = "ERROR:workloadmgr:No snapshot with a name or ID of 'invalid' exists."


service_disable_msg = "workloads service successfully disabled on node: "
service_enable_msg = "workloads service successfully enabled on node: "
wlm_disable_reason = "Trilio Test Reason"
wlm_disable_err_msg = "ERROR:workloadmgr:User does not have admin privileges"
snapshot_reset_err_msg = "ERROR:workloadmgr:Please check service status on the Host("

create_license_expected_str = "End User License Agreement"
create_license_send_str = "y"

migration_vms = ["Automation_Centos8", "Automation_Ubuntu"]
migration_plan_name = "tempest_migration_plan"
migration_plan_desc = "tempest migration plan description"
migration_filename = "/opt/migration.json"
migration_name = "tempest_migration"



