import apscheduler
from apscheduler.schedulers.blocking import BlockingScheduler

#If you want to cleanup all test resources like vms, volumes, workloads then set
# following cleanup parameter value to True otherwise False
cleanup = True 

# pre requisite paramter
pre_req = True

#Test results for reporting
PASS = "PASS"
FAIL = "FAIL"

enabled_tests = ["Attached_Volume_Ceph"]

#Id of workload type "parallel"
parallel="2ddd528d-c9b4-4d7e-8722-cc395140255a"

#Resources to use from file
#Please add your resources one on each line in files: tempest/tempest/vms_file, volumes_file, workloads_file
vms_from_file=False
volumes_from_file=False
workloads_from_file=False

#CLI configuration parameters
workload_type_id="f82ce76f-17fe-438b-aa37-7a023058e50d"
workload_name="clitest"
source_platform="openstack"
snapshot_name = "test-snapshot"
snapshot_type_full = "full"
restore_name = "test-oneclick-restore"
selective_restore_name = "test-selective-restore"
restore_filename = "/opt/restore.json"
vm_license_filename = "test_licenses/tvault_license_20VM.txt"
capacity_license_filename = "test_licenses/tvault_license_1TB.txt"
compute_license_filename = "test_licenses/tvault_license_10compute.txt"
invalid_license_filename = "test_licenses/tvault_license_invalid.txt"
expired_license_filename = "test_licenses/tvault_license_expired.txt"

workload_modify_name = "test2-new"
workload_modify_description = "test2-new-description"
restore_type = "restore"
global_job_scheduler=False

tvault_ip = ["192.168.6.17", "192.168.6.18", "192.168.6.19"]
tvault_dbusername = "root"
tvault_dbname = "workloadmgr"
tvault_password = "sample-password"
wlm_dbusername = "workloadmgr"
wlm_dbpasswd = "sample-password"
wlm_dbhost = "192.168.6.17"

no_of_compute_nodes = 1

# Scheduler parameter

interval="1 hrs"
interval_update = "7 hrs"
enabled='false'
retention_policy_type="Number of Snapshots to Keep"
retention_policy_type_update = "Number of days to retain Snapshots"
retention_policy_value="3"
retention_policy_value_update = "7"
schedule_report_file="scheduleReport.txt"
sched=BlockingScheduler()
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
security_group_name = "test_security"
flavor_name = "test_flavor"
bootfromvol_vol_size = 4
volumes_parts = ["/dev/vdb", "/dev/vdc"]
user_frm_data = "/home/nchavan/tempest/tempest/frm_userdata.sh"

#Email settings data
setting_data = {"smtp_default_recipient": "trilio.build@trilio.io",
                "smtp_default_sender": "trilio.build@trilio.io",
                "smtp_port": "587",
                "smtp_server_name": "smtp.gmail.com",
                "smtp_server_password": tvault_password,
                "smtp_server_username": "trilio.build@trilio.io",
                "smtp_timeout": "10" }
enable_email_notification = {"smtp_email_enable" : 1}
disable_email_notification = {"smtp_email_enable" : 0}


#Parameter for multiple vm workloads etc
vm_count = 8
