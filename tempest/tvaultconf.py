import apscheduler
from apscheduler.schedulers.blocking import BlockingScheduler

#If you want to cleanup all test resources like vms, volumes, workloads then set 
# following cleanup parameter value to True otherwise False
cleanup = False


#Volume type to use by tempest
volume_type="62d6e6ef-c11f-4890-9a27-ee8c0ee05291"

#Id of workload type "parallel"
parallel="2ddd528d-c9b4-4d7e-8722-cc395140255a"

#Resources to use from file 
#Please add your resources one on each line in files: tempest/tempest/vms_file, volumes_file, workloads_file
vms_from_file=False
volumes_from_file=False
workloads_from_file=False



# Scheduler parameter
interval="1 hrs"
enabled='false'
retention_policy_type="Number of Snapshots to Keep"
retention_policy_value="3"
schedule_report_file="scheduleReport.txt"
sched=BlockingScheduler()
count=0
No_of_Backup=3
