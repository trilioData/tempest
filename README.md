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
* How to configure:

    - Update etc/accounts.yaml and provide below:
        - username: 'username' → Username
        - tenant_name: 'project-name' → Project name
        - password: 'password' → Password
        - domain_name: 'default' → Domain name
    - Update etc/tempest.conf and provide below:
        - [compute]
        - flavor_ref = 1 → Flavor ID to be used for instance launch
        - image_ref = fd54c426-caa5-4b0e-85ec-5fd50b4358bc → ID of image to be used for instance launch
        - vm_availability_zone = nova → Nova availability zone for instance launch
        - [volume]
        - volume_availability_zone = nova → Cinder availability zone for volume creation
        - volume_type = ceph → Ceph Volume type name for volume creation 
        - volume_type_id = d6cceecf-a5b8-4b32-995f-3a1e1271ca28 → ID of Ceph volume type specified in volume_type field
        - volume_size = 1 → Size of the volume
        - volume_type_1 = lvm → LVM Volume type name for volume creation
        - volume_type_id_1 = d6cceecf-a5b8-4b32-995f-3a1e1271ca28 → ID of LVM volume type specified in volume_type_1 field
                
        - [identity]
        - auth_version = v3 → Keystone version, v2 or v3
        - admin_domain_name = admin → Domain name of admin user
        - admin_domain_id = 4c0de2d116534c42bcfceffc6e947901 → Domain ID of admin user
        - admin_tenant_id = e5087a90ecc340bd85bbb32171b2fcfe → Tenant ID of admin user
        - admin_tenant_name = cloud-admin-project → Tenant name of admin user
        - admin_password = password → Password of admin user
        - admin_username = cloud-admin → Username of admin user
        - tenant_name = cloud-admin-project → Tenant name of user to be used for executing tests
        - password = password → Password of user to be used for executing tests
        - username = cloud-admin → Username of user to be used for executing tests
        - uri_v3 = http://192.168.1.135:5000/v3 → Auth URL for v3 keystone
        - uri = http://192.168.1.135:5000/v2.0/ → Auth URL for v2 keystone
        - public_endpoint_type = publicURL → Endpoint type used for v2 keystone authentication
        - v3_endpoint_type = publicURL → Endpoint type used for v3 keystone authentication
        - region = RegionOne → Region name
        - disable_ssl_certificate_validation = False → Provide 'True' if SSL is enabled for Openstack endpoint. Else provide 'False'.
        
        - [auth]
        - test_accounts_file = /home/tempest/etc/accounts.yaml → Absolute path of accounts.yaml file to be provided here
        
        - [network]
        - internal_network_id = 0d76ede7-c26c-40b2-bff9-50439eb1ac44 → Network ID to be used for instance launch
        - alt_internal_network_id = ab94b969-5ee0-4b28-850e-4a2942d046ff → Any alternate network ID to be used (for example: network for selective restore)
        
        - [identity-feature-enabled]
        - api_v2 = False → Provide 'True' for v2 keystone, else provide 'False'
        - api_v3 = True → Provide 'True' for v3 keystone, else provide 'False'
        
        - [dashboard]
        - login_url = http://192.168.1.135/auth/login/ → Login URL of openstack horizon
        - dashboard_url = http://192.168.1.135/ → Dashboard URL of openstack horizon
        
        - [wlm]
        - os_tenant_id = 8be245de75d5409f923555f61532a5d0 → ID of 'services' tenant
        - os_cacert = "/opt/tls-ca.pem" → Provide cacert .pem file path here if SSL enabled for WLM endpoint
        - op_db_password = "sample-password" → Mysql 'root' password of openstack controller for config backup
        
    - Update tempest/tvaultconf.py and provide below:
        - tvault_ip = "192.168.1.113" → IP of TrilioVault appliance configured with respective openstack
        - tvault_dbpassword = "sample-password" → TrilioVault appliance root password
        - compute_node_ip = "192.168.1.189" → Compute node IP for config backup verification
        - compute_node_username = "root" → Compute node username for config backup verification
        - compute_node_password = "password" → Compute node password for config backup verification
                

* How to run tests:

    - All tempest tests are run on virtual environment.
    - Install below packages required for virtual environment.
        - yum install gcc
        - yum install python-virtualenv 
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

* There is need for workloadmgr client installation when the test case is testing CLI. For sanity tests example, all the tests are API based, so it'll not be necessary to install workloadmgr client in virtual env. Install it by adding workloadmgr client to requirement.txt.

* Also, for CLI based test cases, having openstack's rc file sourced (environment variables populated) is mandatory before trigerring any test cases. 

Following env variables are needed for workloadmgr test cases to work:

    OS_TENANT_ID
    OS_TENANT_NAME
    OS_PROJECT_DOMAIN_NAME
    OS_DOMAIN_ID
    OS_DOMAIN_NAME
    OS_USER_DOMAIN_ID


* Adding the license to triliovault is a mandatory for any succeeding test case. You can add it to triliovault by CLI/UI. Please use license file provided at tempest/test_licenses/tvault_license_10VM.txt for Sanity test.

* For running Sanity Test scenario - 

      ./run_tempest.sh tempest.api.workloadmgr.sanity.test_create_full_snapshot
      
      Test Results - test_results
      
      Test Log - tempest.log 
