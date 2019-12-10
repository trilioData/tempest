# automation
Repo for automation build, test etc.

* Features:
    - Run test suites
    - Run individual tests
    - Test reporting
    - Detailed logging
    - Execute prerequisites at test suite level in order to reuse resources and reduce execution time

* Download tempest:

* Download TrilioData tempest framework from GitHub using command:

* git clone https://github.com/trilioData/tempest.git
* How to configure tempest:

    - Update the openstack setup details in openstack-setup.conf file 
    - Run the wrapper script fetch_resources.sh
      ./fetch_resources.sh
    - Update tempest/tvaultconf.py and provide below:
        - tvault_password = "sample password" → TrilioVault appliance root password
                
* How to run tests:

    - All tempest tests are run on virtual environment.
    - Install below packages required for virtual environment.
        - yum install gcc
        - yum install python-virtualenv 
    - Install python-workloadmgrclient package from TrilioVault appliance.
    - To create virtual environment:
        - Run below:
            - python tools/install_venv.py
    - To run a single test:
        - Edit run_tempest.sh and add below at the starting of the file.
            source /root/wlmadminrc 
        - This rc file is required for executing Workloadmanager CLI commands. Make sure to provide absolute path of the rc file.
        - Execute run_tempest.sh file with required script as argument
            - ./run_tempest.sh tempest.api.workloadmgr.workload.test_tvault1033_create_workload
        - Log file "tempest.log" would be available
    - To run a sanity tests:
        - Update below field in tempest/tvaultconf.py file as per the volume types available on the openstack setup.
             - If openstack setup has only LVM cinder type configured:
               enabled_tests = ["Attached_Volume_LVM","Boot_from_Volume_LVM"] 
             - If openstack setup has only Ceph cinder type configured:
               enabled_tests = ["Attached_Volume_Ceph","Boot_from_Volume_Ceph"] 
             - If openstack setup has both LVM and Ceph cinder types configured:
               enabled_tests = ["Attached_Volume_LVM","Attached_Volume_Ceph","Boot_from_Volume_LVM","Boot_from_Volume_Ceph"] 
        - Run below:
            - chmod +x sanity-run.sh 
            - ./sanity-run.sh 
        - Log file will be available in "logs/" directory
    - To run a suite:
        - Edit master-run.sh and add below at the starting of the file.
            source /root/wlmadminrc 
        - This rc file is required for executing Workloadmanager CLI commands. Make sure to provide absolute path of the rc file.
        - Update master-run.sh file with required suite details:
            - SUITE_LIST=("tempest.api.workloadmgr.workload") 
        - Now run below:
            - ./master-run.sh 
        - Log files would be available in "logs/" directory.
     - If a virtual env already exists, tempest uses the existing one for test execution. Else it would prompt the user to create a new virtual env.

* Test Coverage:

    - Licensing tests
    - Workload tests
    - Snapshot tests
    - Restore tests (Note - This needs min. 2 Floating IPs configureed on Openstack)
        - One click restore
        - Selective restore
        - In-place restore
    - File search tests
    - Configuration backup suite
    - Upgrade scenarios tests
    - Workload Policy tests
    - Workload Modify
    - Scale Testing tests
    - Chargeback tests
    - Sanity tests
    - RBAC tests
    - Scheduler tests

* NOTES

* For TrilioVault version 3.2 and below, need to install python-workloadmgrclient pip package on the system as well as on the virtual environment.

* For TrilioVault version 3.3 and above, need to install python-workloadmgrclient rpm/deb package on the system.

* Also, for CLI based test cases, having openstack's rc file sourced (environment variables populated) is mandatory before trigerring any test cases. 

Following env variables are needed for workloadmgr test cases to work:

    OS_TENANT_ID
    OS_TENANT_NAME
    OS_PROJECT_DOMAIN_NAME
    OS_DOMAIN_ID
    OS_DOMAIN_NAME
    OS_USER_DOMAIN_ID
    OS_USERNAME
    OS_PASSWORD
    OS_AUTH_URL
    OS_IDENTITY_API_VERSION
    OS_INTERFACE

* Adding the license to triliovault is a mandatory for any succeeding test case. You can add it to triliovault by CLI/UI.

* For running Sanity Test scenario - 

      ./run_tempest.sh tempest.api.workloadmgr.sanity.test_create_full_snapshot
      
      Test Results - test_results
      
      Test Log - tempest.log 
