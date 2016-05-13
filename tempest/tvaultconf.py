#If you want to cleanup all test resources like vms, volumes, workloads then set 
# following cleanup parameter value to True otherwise False
cleanup = False


#Volume type to use by tempest
volume_type="0db411bb-1c21-4e22-8ab8-9ad181ac451c"

#Id of workload type "parallel"
parallel="2ddd528d-c9b4-4d7e-8722-cc395140255a"

#Resources to use from file 
#Please add your resources one on each line in files: tempest/tempest/vms_file, volumes_file, workloads_file
vms_from_file=True
volumes_from_file=True
workloads_from_file=False
