# automation
Repo for automation build, test etc.

* Features:
    - Run test suites
    - Run individual tests
    - Test reporting
    - Detailed logging
    - Execute prerequisites at test suite level in order to reuse resources and reduce execution time

* Supported Operating systems & Python versions:
    - CentOS 7 with Python 2.7
    - CentOS 8 with Python 3.6
    - Ubuntu 18.04 with Python 3.6

* Download tempest:
    - Download TrilioData tempest framework from GitHub using command:
      ```
      git clone -b v4.0maintenance https://github.com/trilioData/tempest.git
      cd tempest/
      ```
      
* Prerequisites:
    - CentOS 7
         - Install required packages
           ```
           yum install gcc python-virtualenv -y
           easy_install pip
           pip install apscheduler
           ```

         - Install WLM client
           ```
           cat > /etc/yum.repos.d/trilio.repo <<-EOF
           [trilio]
           name=Trilio Repository
           baseurl=http://{TVAULT_IP}:8085/yum-repo/queens/
           enabled=1
           gpgcheck=0
           EOF
           yum install python-workloadmgrclient -y
           ```

         - Run below script to create virtual environment:
           ```
           python tools/install_venv.py
            ```
    - CentOS 8
         - Install required packages
           ```
           yum install gcc python3-venv -y
           pip3 install apscheduler
           ```

         - Install WLM client
           ```
           cat > /etc/yum.repos.d/trilio.repo <<-EOF
           [trilio]
           name=Trilio Repository
           baseurl=http://{TVAULT_IP}:8085/yum-repo/queens/
           enabled=1
           gpgcheck=0
           EOF
           yum install python3-workloadmgrclient -y
           ```
           
         - Run below script to create virtual environment:
           ```
           python3 tools/install_venv.py
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

         - Run below script to create virtual environment:
           ```
           python3 tools/install_venv.py
            ```
* Configure tempest:

    - Update the openstack setup details in openstack-setup.conf file 
    - Run the wrapper script fetch_resources.sh
      ```
      ./fetch_resources.sh
      ```
    - Update tempest/tvaultconf.py and provide below:
        - tvault_password = "sample password" → TrilioVault appliance root password
                
* How to run tests:

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

* Test Coverage:

    - Licensing tests
    - Workload tests
    - Snapshot tests
    - Restore tests (Note - This needs min. 2 Floating IPs configureed on Openstack)
        - One click restore
        - Selective restore
        - In-place restore
    - File search tests
    - Workload Policy tests
    - Workload Modify
    - Chargeback tests
    - Sanity tests
    - RBAC tests

* NOTES

* Adding the license to triliovault is a mandatory for any succeeding test case. You can add it to triliovault by CLI/UI. 
