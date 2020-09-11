# TrilioVault tempest

1. Features:
    - Run test suites
    - Run individual tests
    - Test reporting
    - Detailed logging
    - Execute prerequisites at test suite level in order to reuse resources and reduce execution time

2. Supported Operating systems & Python versions:
    - CentOS 7 with Python 2.7
    - CentOS 8 with Python 3.6
    - Ubuntu 16.04 with Python 2.7
    - Ubuntu 18.04 with Python 3.6

3. Download tempest:
    - Download TrilioData tempest framework from GitHub using command:
      ```
      git clone -b v4.0maintenance https://github.com/trilioData/tempest.git
      cd tempest/
      ```
      
4. Prerequisites:
    - CentOS 7
         - Install required packages
           ```
           yum install gcc python-virtualenv -y
           easy_install pip
           pip install apscheduler
           ```

         - Install WLM client
           To ensure installation of dependent packages, please add the below repo.
           ```
           yum install centos-release-openstack-train -y
           cat > /etc/yum.repos.d/trilio.repo <<-EOF
           [trilio]
           name=Trilio Repository
           baseurl=http://{TVAULT_IP}:8085/yum-repo/queens/
           enabled=1
           gpgcheck=0
           EOF
           yum install workloadmgrclient -y
           ```

         - All the tempest tests would run inside a virtual environment. Run below script to create virtual environment:
           ```
           python tools/install_venv.py
            ```
    - CentOS 8
         - Install required packages
           ```
           yum install gcc python3-virtualenv -y
           pip3 install apscheduler
           ```

         - Install WLM client
           To ensure installation of dependent packages, please add the below repo.
           ```
           yum install centos-release-openstack-train -y
           cat > /etc/yum.repos.d/trilio.repo <<-EOF
           [trilio]
           name=Trilio Repository
           baseurl=http://{TVAULT_IP}:8085/yum-repo/queens/
           enabled=1
           gpgcheck=0
           EOF
           yum install python3-workloadmgrclient-el8 -y
           ```
           
         - All the tempest tests would run inside a virtual environment. Run below script to create virtual environment:
           ```
           python3 tools/install_venv.py
            ```
    - Ubuntu 16.04
         - Install required packages
           ```
           apt-get install gcc virtualenv python-pip -y
           pip install apscheduler
           ```

         - Install WLM client
           ```
           cat > /etc/apt/sources.list.d/trilio.list <<-EOF
           deb [trusted=yes] https://apt.fury.io/triliodata-4-0/ /
           EOF
           apt-get update
           apt-get install python-workloadmgrclient -y
           ```

         - All the tempest tests would run inside a virtual environment. Run below script to create virtual environment:
           ```
           python tools/install_venv.py
            ```
    - Ubuntu 18.04
         - Install required packages
           ```
           apt-get install gcc python3-venv python3-pip -y
           pip3 install apscheduler
           ```

         - Install WLM client
           ```
           cat > /etc/apt/sources.list.d/trilio.list <<-EOF
           deb [trusted=yes] https://apt.fury.io/triliodata-4-0/ /
           EOF
           apt-get update
           apt-get install python3-workloadmgrclient -y
           ```

         - All the tempest tests would run inside a virtual environment. Run below script to create virtual environment:
           ```
           python3 tools/install_venv.py
            ```

5. Configure tempest:

    - Update the openstack setup details in openstack-setup.conf file 
      ```
      ######## Openstack setup details ########

      ## OS_AUTH_URL from openstack rc file
      AUTH_URL=https://192.168.6.196:5000/v3 
      
      ## OS_REGION_NAME from openstack rc file
      REGION_NAME=USEAST   
      
      ## OS_IDENTITY_API_VERSION from openstack rc file
      IDENTITY_API_VERSION=3

      ## Name of the image that is to be used for instance launch
      TEST_IMAGE_NAME=cirros
      
      ## Size of the volume to be created for WLM tests
      VOLUME_SIZE=1
      
      ## Name of the TrilioVault File recovery manager image on Openstack
      FVM_IMAGE_NAME=fvm
      
      ## List of cinder backends enabled on the Openstack.
      ## If only default cinder type is available on your setup, give the value as CINDER_BACKENDS_ENABLED=()
      CINDER_BACKENDS_ENABLED=(ceph iscsi)
      
      ## OS_ENDPOINT_TYPE from openstack rc file
      ENDPOINT_TYPE=publicURL

      ### Cloud Admin details ###
      ## In case of multidomain setup, provide cloud admin details here
      ## In case of non-multidomain setup, provide the admin details here
      CLOUDADMIN_USERNAME=cloudadmin
      CLOUDADMIN_PASSWORD=Password1!
      CLOUDADMIN_DOMAIN_NAME=clouddomain
      CLOUDADMIN_USER_DOMAIN_NAME=clouddomain
      CLOUDADMIN_PROJECT_NAME=cloudproject
      CLOUDADMIN_PROJECT_ID=cd75812d91b54329b4448209593b12cc

      ### Test user details ###
      ## Provide the details of the user and project that is to be used for running WLM tests 
      
      TEST_USERNAME=trilio-member
      TEST_PASSWORD=password
      TEST_DOMAIN_NAME=trilio-domain
      TEST_USER_DOMAIN_NAME=trilio-domain
      TEST_PROJECT_NAME=trilio-project-1
      TEST_ALT_PROJECT_NAME=trilio-project-2

      ######## TrilioVault details ########
      ## List of TrilioVault IPs configured with the Openstack setup
      TVAULT_IP=(192.168.6.17 192.168.6.18 192.168.6.19)

      ###### Python version details #######
      ## Provide the python version to be used for running WLM tests. 
      ## This should match with the python version of workloadmgrclient package installed on your machine
      PYTHON_VERSION=3
      ```
    
    - Run the wrapper script fetch_resources.sh to pull the openstack details required for tempest configuration. This also takes care of required resources for WLM tests such as network, router and user.
      ```
      ./fetch_resources.sh
      ```
    - Update tempest/tvaultconf.py and provide below. This is required for database validation tests.
        - tvault_password = "sample password" → TrilioVault appliance root password
                
6. How to run tests:

    - All tempest tests are run on virtual environment.
    - To run a single test:
        - Execute run_tempest.sh file with required script as argument
          ```
          ./run_tempest.sh tempest.api.workloadmgr.workload.test_tvault1033_create_workload
          ```
        - Log file "tempest.log" would be available
    - To run sanity tests, run below:
        ```
        ./sanity-run.sh
        ```
        - Log file will be available in "logs/" directory
    - To run a suite:
        - Update master-run.sh file with required suite details:
            - SUITE_LIST=("tempest.api.workloadmgr.workload") 
        - Now run below:
            ```
            ./master-run.sh 
            ```
        - Log files would be available in "logs/" directory.
     - If a virtual env already exists, tempest uses the existing one for test execution. Else it would prompt the user to create a new virtual env.

7. Test Coverage:

    - Licensing tests
    - Workload tests
    - Snapshot tests
    - Restore tests (Note - This needs min. 2 Floating IPs configured on Openstack)
        - One click restore
        - Selective restore
        - In-place restore
    - File search tests
    - Workload Policy tests
    - Workload Modify
    - Chargeback tests
    - Sanity tests
    - RBAC tests

8. NOTES

    - Adding the license to triliovault is a mandatory for any succeeding test case. You can add it to triliovault by CLI/UI. 
