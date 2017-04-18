import apscheduler
from apscheduler.schedulers.blocking import BlockingScheduler

#If you want to cleanup all test resources like vms, volumes, workloads then set
# following cleanup parameter value to True otherwise False
cleanup = False

#Volume type to use by tempest
volume_type="5a745b43-57cf-4fc4-9a5f-d296c0f1e5b3"

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
snapshot_name = "test2-snapshot"
snapshot_type_full = "full"
restore_name = "test-oneclick-restore"
selective_restore_name = "test-selective-restore"
restore_filename = "/opt/stack/python-workloadmgrclient/input-files/restore.json"
workload_modify_name = "test2-new"
workload_modify_description = "test2-new-description"
restore_type = "restore"
volume_size = 1
internal_network_id = "f806f7a0-93b0-47f6-bf68-32ee66bddbaf"

tvault_ip = "192.168.1.116"
tvault_dbusername = "root"
tvault_dbpassword = "52T8FVYZJse"
tvault_dbname = "workloadmgr"
compute_ip = "192.168.1.21"
compute_username = "root"
compute_passwd = "Password1!"

# Scheduler parameter
interval="1 hrs"
enabled='false'
retention_policy_type="Number of Snapshots to Keep"
retention_policy_value="3"
schedule_report_file="scheduleReport.txt"
sched=BlockingScheduler()
count=0
No_of_Backup=1
