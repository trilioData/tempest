#!/bin/bash
source openstack-setup.conf

PYTHON_VERSION=3
TEMPEST_DIR=$PWD
TEMPEST_CONFIG_DIR=${TEMPEST_CONFIG_DIR:-$TEMPEST_DIR/etc}
TEMPEST_CONFIG=$TEMPEST_CONFIG_DIR/tempest.conf
TEMPEST_STATE_PATH=${TEMPEST_STATE_PATH:-$TEMPEST_DIR/lock}
TEMPEST_ACCOUNTS=$TEMPEST_CONFIG_DIR/accounts.yaml
TEMPEST_FRM_FILE=$TEMPEST_DIR/tempest/frm_userdata.sh
TEMPEST_TVAULTCONF=$TEMPEST_DIR/tempest/tvaultconf.py
OPENSTACK_CLI_VENV=$TEMPEST_DIR/.myenv
TEMPEST_VENV_DIR=$TEMPEST_DIR/.venv
NONADMIN_USERNAME=trilio-nonadmin-user
NONADMIN_PWD=password
NEWADMIN_USERNAME=trilio-newadmin-user
NEWADMIN_PWD=password
BACKUP_USERNAME=trilio-backup-user
BACKUP_PWD=password
ADMIN2_USERNAME=trilio-admin2-user
ADMIN2_PWD=password
ADMIN2_MAILID=test1@trilio.io
git checkout run_tempest.sh

sed -i "2i export PYTHON_VERSION=$PYTHON_VERSION" run_tempest.sh
sed -i "/PYTHON_CMD=/c PYTHON_CMD=\"$TEMPEST_VENV_DIR/bin/python$PYTHON_VERSION\"" sanity-run.sh
sed -i "/PYTHON_CMD=/c PYTHON_CMD=\"$TEMPEST_VENV_DIR/bin/python$PYTHON_VERSION\"" master-run.sh

if [[ "$AUTH_URL" =~ "https" ]]
then
    OPENSTACK_CMD="openstack --insecure"
    sed -i 's/workloadmgr /workloadmgr --insecure /g' tempest/command_argument_string.py
else
    OPENSTACK_CMD="openstack"
fi

function ini_has_option {
    local xtrace
    xtrace=$(set +o | grep xtrace)
    set +o xtrace
    local sudo=""
    if [ $1 == "-sudo" ]; then
        sudo="sudo "
        shift
    fi
    local file=$1
    local section=$2
    local option=$3
    local line

    line=$($sudo sed -ne "/^\[$section\]/,/^\[.*\]/ { /^$option[ \t]*=/ p; }" "$file")
    $xtrace
    [ -n "$line" ]
}

function iniset {
    local xtrace
    xtrace=$(set +o | grep xtrace)
    set +o xtrace
    local sudo=""
    local sudo_option=""
    if [ $1 == "-sudo" ]; then
        sudo="sudo "
        sudo_option="-sudo "
        shift
    fi
    local file=$1
    local section=$2
    local option=$3
    local value=$4

    if [[ -z $section || -z $option ]]; then
        $xtrace
        return
    fi

    if ! $sudo grep -q "^\[$section\]" "$file" 2>/dev/null; then
        # Add section at the end
        echo -e "\n[$section]" | $sudo tee --append "$file" > /dev/null
    fi
    if ! ini_has_option $sudo_option "$file" "$section" "$option"; then
        # Add it
        $sudo sed -i -e "/^\[$section\]/ a\\
$option = $value
" "$file"
    else
        local sep
        sep=$(echo -ne "\x01")
        # Replace it
        $sudo sed -i -e '/^\['${section}'\]/,/^\[.*\]/ s'${sep}'^\('"${option}"'[ \t]*=[ \t]*\).*$'${sep}'\1'"${value}"${sep} "$file"
    fi
    $xtrace
}

function image_size_in_gib {
    local size
    size=$($OPENSTACK_CMD image show $1 -c size -f value)
    echo $size | python -c "import math; print int(math.ceil(float(int(raw_input()) / 1024.0 ** 3)))"
}

function configure_tempest 
{
    # Save IFS
    ifs=$IFS
	
    if [[ "$AUTH_URL" =~ "https" ]]
    then
        iniset $TEMPEST_CONFIG identity disable_ssl_certificate_validation True
        iniset $TEMPEST_CONFIG wlm insecure True
    fi

    # Oslo
    iniset $TEMPEST_CONFIG DEFAULT use_stderr False
    iniset $TEMPEST_CONFIG DEFAULT use_syslog False
    iniset $TEMPEST_CONFIG DEFAULT log_file tempest.log
    iniset $TEMPEST_CONFIG DEFAULT debug True

    iniset $TEMPEST_CONFIG oslo_concurrency lock_path $TEMPEST_STATE_PATH
    mkdir -p $TEMPEST_STATE_PATH

    # Set cloud admin credentials
    echo "Setting cloud admin credentials, to fetch openstack details\n"
    export OS_USERNAME=$CLOUDADMIN_USERNAME
    export OS_PASSWORD=$CLOUDADMIN_PASSWORD
    export OS_PROJECT_DOMAIN_NAME=$CLOUDADMIN_DOMAIN_NAME
    export OS_USER_DOMAIN_NAME=$CLOUDADMIN_USER_DOMAIN_NAME
    export OS_PROJECT_NAME=$CLOUDADMIN_PROJECT_NAME
    export OS_PROJECT_ID=$CLOUDADMIN_PROJECT_ID
    unset OS_TENANT_ID
    unset OS_TENANT_NAME
    export OS_AUTH_URL=$AUTH_URL
    export OS_IDENTITY_API_VERSION=$IDENTITY_API_VERSION
    export OS_REGION_NAME=$REGION_NAME
    export OS_ENDPOINT_TYPE=$ENDPOINT_TYPE
    export OS_INTERFACE=$ENDPOINT_TYPE

    #Create roles and users
    $OPENSTACK_CMD role create newadmin
    $OPENSTACK_CMD role create backup
    $OPENSTACK_CMD user create --domain $TEST_DOMAIN_NAME --email test@trilio.io --password $NONADMIN_PWD --description $NONADMIN_USERNAME --enable $NONADMIN_USERNAME
    $OPENSTACK_CMD user create --domain $TEST_DOMAIN_NAME --email test@trilio.io --password $NEWADMIN_PWD --description $NEWADMIN_USERNAME --enable $NEWADMIN_USERNAME
    $OPENSTACK_CMD user create --domain $TEST_DOMAIN_NAME --email test@trilio.io --password $BACKUP_PWD --description $BACKUP_USERNAME --enable $BACKUP_USERNAME
    $OPENSTACK_CMD user create --domain $TEST_DOMAIN_NAME --email $ADMIN2_MAILID --password $ADMIN2_PWD --description $ADMIN2_USERNAME --enable $ADMIN2_USERNAME
    $OPENSTACK_CMD role add --user $TEST_USERNAME --user-domain $TEST_DOMAIN_NAME --project $TEST_PROJECT_NAME $TRUSTEE_ROLE
    $OPENSTACK_CMD role add --user $TEST_USERNAME --user-domain $TEST_DOMAIN_NAME --project $TEST_ALT_PROJECT_NAME $TRUSTEE_ROLE
    $OPENSTACK_CMD role add --user $NONADMIN_USERNAME --user-domain $TEST_DOMAIN_NAME --project $TEST_PROJECT_NAME $TRUSTEE_ROLE
    $OPENSTACK_CMD role add --user $NONADMIN_USERNAME --user-domain $TEST_DOMAIN_NAME --project $TEST_ALT_PROJECT_NAME $TRUSTEE_ROLE
    $OPENSTACK_CMD role add --user $NEWADMIN_USERNAME --user-domain $TEST_DOMAIN_NAME --project $TEST_PROJECT_NAME $TRUSTEE_ROLE
    $OPENSTACK_CMD role add --user $NEWADMIN_USERNAME --user-domain $TEST_DOMAIN_NAME --project $TEST_PROJECT_NAME newadmin
    $OPENSTACK_CMD role add --user $BACKUP_USERNAME --user-domain $TEST_DOMAIN_NAME --project $TEST_PROJECT_NAME $TRUSTEE_ROLE
    $OPENSTACK_CMD role add --user $BACKUP_USERNAME --user-domain $TEST_DOMAIN_NAME --project $TEST_PROJECT_NAME backup
    $OPENSTACK_CMD role add --user $ADMIN2_USERNAME --user-domain $TEST_DOMAIN_NAME --project $TEST_PROJECT_NAME $TRUSTEE_ROLE
    $OPENSTACK_CMD role add --user $ADMIN2_USERNAME --user-domain $TEST_DOMAIN_NAME --project $TEST_PROJECT_NAME admin

    #Fetch identity data
    admin_domain_id=$($OPENSTACK_CMD domain list | awk "/ $CLOUDADMIN_DOMAIN_NAME / { print \$2 }")
    test_domain_id=$($OPENSTACK_CMD domain list | awk "/ $TEST_DOMAIN_NAME / { print \$2 }")
    test_project_id=$($OPENSTACK_CMD project list | awk "/ $TEST_PROJECT_NAME / { print \$2 }")
    test_alt_project_id=$($OPENSTACK_CMD project list | awk "/ $TEST_ALT_PROJECT_NAME / { print \$2 }")
    service_project_id=$($OPENSTACK_CMD project list | awk "/service*/ { print \$2 }")
    test_user_id=$($OPENSTACK_CMD user list --domain $TEST_DOMAIN_NAME | awk "/ $TEST_USERNAME / { print \$2 }")
    test_alt_user_id=$($OPENSTACK_CMD user list --domain $TEST_DOMAIN_NAME | awk "/ $NONADMIN_USERNAME / { print \$2 }")
    wlm_endpoint=$($OPENSTACK_CMD endpoint list |  awk "/workloads/" | awk "/public/ { print \$14 }")
    $OPENSTACK_CMD endpoint list | grep barbican
    if [ $? -ne 0 ]
    then
	iniset $TEMPEST_CONFIG service_available key_manager False
    else
	iniset $TEMPEST_CONFIG service_available key_manager True
    fi

    unset OS_PROJECT_DOMAIN_NAME
    export OS_PROJECT_DOMAIN_ID=$admin_domain_id

    if [[ "$wlm_endpoint" =~ "https" ]]
    then
        git checkout tempest/command_argument_string.py
        sed -i 's/workloadmgr /workloadmgr --insecure /g' tempest/command_argument_string.py
        sed -i 's/openstack /openstack --insecure /g' tempest/command_argument_string.py
        iniset $TEMPEST_CONFIG wlm insecure True
    fi

    # Volume
    echo "Fetching volume type details\n"
    volume_az=$($OPENSTACK_CMD availability zone list --volume | awk "/ available / { print \$2 }")
    shopt -s nocasematch
    CINDER_BACKENDS_ENABLED=($(echo ${CINDER_BACKENDS_ENABLED[@]} | tr [:space:] '\n' | awk '!x[$0]++'))
    case "${#CINDER_BACKENDS_ENABLED[*]}" in
        0)
            echo "No volume type available to use, using Default \n"
            type="DEFAULT"
            type_id=$($OPENSTACK_CMD volume type list | grep -i $type | awk '$2 && $2 != "ID" {print $2}')
            volume_type=$type
            volume_type_id=$type_id
            volume_types=$type":"$type_id
            enabled_tests=[\"Attached_Volume_"$type\"",\"Boot_from_Volume_"$type\""]
            ;;
        *)
            cnt=0
            for type in ${CINDER_BACKENDS_ENABLED[@]}; do
                type_id=$($OPENSTACK_CMD volume type list | grep -i " $type " | awk '$2 && $2 != "ID" {print $2}')
                if [ $cnt -eq 0 ]
                then
                    volume_type=$type
                    volume_type_id=$type_id
                    volume_types=$type":"$type_id
                    enabled_tests=[\"Attached_Volume_"$type\"",\"Boot_from_Volume_"$type\""
                else
                    volume_types+=,$type":"$type_id
                    enabled_tests+=,\"Attached_Volume_"$type\"",\"Boot_from_Volume_"$type\""
                fi
                cnt=$((cnt+1))
            done
            enabled_tests+=]
    esac
    
    declare -a images

    echo "Fetching image details\n"
    while read -r IMAGE_NAME IMAGE_UUID; do
        if [ "$IMAGE_NAME" = "$TEST_IMAGE_NAME" ]; then
            image_uuid="$IMAGE_UUID"
            image_uuid_alt="$IMAGE_UUID"
        fi
        images+=($IMAGE_UUID)
    done < <($OPENSTACK_CMD image list --property status=active | awk -F'|' '!/^(+--)|ID|aki|ari/ { print $3,$2 }')

    case "${#images[*]}" in
        0)
            echo "Found no valid images to use!\n"
            exit 1
            ;;
        1)
            if [ -z "$image_uuid" ]; then
                image_uuid=${images[0]}
                image_uuid_alt=${images[0]}
            fi
            ;;
        *)
            if [ -z "$image_uuid" ]; then
                image_uuid=${images[0]}
                image_uuid_alt=${images[1]}
            fi
            ;;
    esac

    cnt=0
    for name in ${FVM_IMAGE_NAMES[@]}; do
        id=$($OPENSTACK_CMD image list | grep -i "$name " | awk '$2 && $2 != "ID" {print $2}')
        if [ $cnt -eq 0 ]
        then
            frm_data=$name':'$id
        else
            frm_data=$frm_data','$name':'$id
        fi
	cnt=$((cnt+1))
    done

    echo "Fetching flavor details\n"
    available_flavors=$($OPENSTACK_CMD flavor list)
    if [[ ! ( $available_flavors =~ $TEST_IMAGE_NAME ) ]] ; then
        if [[ $TEST_IMAGE_NAME =~ "cirros" ]] ; then
            $OPENSTACK_CMD flavor create --ram 64 --disk 1 --vcpus 1 $TEST_IMAGE_NAME
        else
            $OPENSTACK_CMD flavor create --ram 2048 --disk 20 --vcpus 2 $TEST_IMAGE_NAME
        fi
    fi
    for name in ${FVM_IMAGE_NAMES[@]}; do
      if [[ ! ( $available_flavors =~ $name ) ]] && [[ "$frm_data" ]]; then
        # Determine the flavor disk size based on the image size.
        $OPENSTACK_CMD flavor create --ram 2048 --disk 14 --vcpus 2 $name
      fi
    done

    available_flavors=$($OPENSTACK_CMD flavor list)
    IFS=$'\r\n'
    flavors=""
    fvm_flavor=""
    for line in $available_flavors; do
        f=$(echo $line | awk "/ $TEST_IMAGE_NAME / { print \$2 }")
        flavors="$flavors $f"
        for name in ${FVM_IMAGE_NAMES[@]}; do
          f1=$(echo $line | awk "/ $name / { print \$2 }")
          fvm_flavor="$fvm_flavor $f1"
        done
    done

    echo $flavors
    echo $fvm_flavor
    for line in $flavors; do
        flavors="$flavors `echo $line | grep -v "^\(|\s*ID\|+--\)" | cut -d' ' -f2`"
    done
    for line in $fvm_flavor; do
        fvm_flavor="$fvm_flavor `echo $line | grep -v "^\(|\s*ID\|+--\)" | cut -d' ' -f2`"
    done
    IFS=" "
    flavors=($flavors)
    num_flavors=${#flavors[*]}
    echo "Found $num_flavors flavors"
    if [[ $num_flavors -eq 0 ]]; then
        echo "Found no valid flavors to use!"
        exit 1
    fi
    flavor_ref=${flavors[0]}
    fvm_flavor=($fvm_flavor)
    num_fvm_flavor=${#fvm_flavor[*]}
    echo "Found $num_fvm_flavor flavors for File manager"
    if [[ $num_fvm_flavor -eq 0 ]]; then
        echo "Found no valid fvm flavors to use!\n"
    fi
    flavor_ref_alt=${fvm_flavor[0]}

    compute_az=$($OPENSTACK_CMD availability zone list --long | awk "/ nova-compute / " | awk "/ available / { print \$2 }" | tail -1)
    no_of_computes=$($OPENSTACK_CMD compute service list | awk "/ nova-compute / " | wc -l)

    iniset $TEMPEST_CONFIG compute image_ref $image_uuid
    iniset $TEMPEST_CONFIG compute fvm_image_ref $frm_data
    iniset $TEMPEST_CONFIG compute flavor_ref $flavor_ref
    iniset $TEMPEST_CONFIG compute flavor_ref_alt $flavor_ref_alt
    iniset $TEMPEST_CONFIG compute vm_availability_zone $compute_az

    iniset $TEMPEST_CONFIG volume volume_availability_zone $volume_az
    iniset $TEMPEST_CONFIG volume volume_type $volume_type
    iniset $TEMPEST_CONFIG volume volume_type_id $volume_type_id
    iniset $TEMPEST_CONFIG volume volume_types $volume_types
    iniset $TEMPEST_CONFIG volume volume_size $VOLUME_SIZE

    # Identity
    iniset $TEMPEST_CONFIG identity auth_version v3
    iniset $TEMPEST_CONFIG identity admin_domain_id $admin_domain_id
    iniset $TEMPEST_CONFIG identity admin_tenant_id $CLOUDADMIN_PROJECT_ID
    iniset $TEMPEST_CONFIG identity tenant_name $TEST_PROJECT_NAME
    iniset $TEMPEST_CONFIG identity tenant_name_1 $TEST_ALT_PROJECT_NAME
    iniset $TEMPEST_CONFIG identity password $TEST_PASSWORD
    iniset $TEMPEST_CONFIG identity username $TEST_USERNAME
    iniset $TEMPEST_CONFIG identity project_name $TEST_PROJECT_NAME
    iniset $TEMPEST_CONFIG identity project_alt_name $TEST_ALT_PROJECT_NAME
    iniset $TEMPEST_CONFIG identity domain_name $TEST_USER_DOMAIN_NAME
    iniset $TEMPEST_CONFIG identity tenant_id $test_project_id
    iniset $TEMPEST_CONFIG identity tenant_id_1 $test_alt_project_id
    iniset $TEMPEST_CONFIG identity user_id $test_user_id
    iniset $TEMPEST_CONFIG identity user_id_1 $test_alt_user_id
    iniset $TEMPEST_CONFIG identity domain_id $test_domain_id
    iniset $TEMPEST_CONFIG identity default_domain_id $test_domain_id
    iniset $TEMPEST_CONFIG identity uri_v3 $OS_AUTH_URL
    iniset $TEMPEST_CONFIG identity v3_endpoint_type $ENDPOINT_TYPE
    iniset $TEMPEST_CONFIG identity region $OS_REGION_NAME

    iniset $TEMPEST_CONFIG identity nonadmin_user $NONADMIN_USERNAME
    iniset $TEMPEST_CONFIG identity nonadmin_password $NONADMIN_PWD
    iniset $TEMPEST_CONFIG identity newadmin_user $NEWADMIN_USERNAME
    iniset $TEMPEST_CONFIG identity newadmin_password $NEWADMIN_PWD
    iniset $TEMPEST_CONFIG identity backupuser $BACKUP_USERNAME
    iniset $TEMPEST_CONFIG identity backupuser_password $BACKUP_PWD

    # Auth
    iniset $TEMPEST_CONFIG auth use_dynamic_credentials False
    iniset $TEMPEST_CONFIG auth test_accounts_file $TEMPEST_ACCOUNTS
    iniset $TEMPEST_CONFIG auth allow_tenant_isolation True
    iniset $TEMPEST_CONFIG auth admin_username $CLOUDADMIN_USERNAME
    iniset $TEMPEST_CONFIG auth admin_password $CLOUDADMIN_PASSWORD
    iniset $TEMPEST_CONFIG auth admin_project_name $CLOUDADMIN_PROJECT_NAME
    iniset $TEMPEST_CONFIG auth admin_domain_name $CLOUDADMIN_DOMAIN_NAME

    env | grep OS_
    conn_str=`workloadmgr --insecure setting-list --get_hidden True -f value | grep sql_connection`
    echo "sql_connection: "$conn_str
    dbusername=`echo $conn_str | cut -d '/' -f 3 | cut -d ':' -f 1`
    mysql_wlm_pwd=`echo $conn_str | cut -d '/' -f 3 | cut -d ':' -f 2 | cut -d '@' -f 1`
    mysql_ip=`echo $conn_str | cut -d '/' -f 3 | cut -d ':' -f 2 | cut -d '@' -f 2`
    dbname=`echo $conn_str | cut -d '/' -f 4 | cut -d '?' -f1`
    tvault_version=`workloadmgr --insecure workload-get-nodes -f yaml | grep -i version | cut -d ':' -f2 | head -1 | xargs`

    #Set test user credentials
    echo "Set test user credentials\n"
    unset OS_PROJECT_ID
    unset OS_PROJECT_DOMAIN_ID
    export OS_USERNAME=$TEST_USERNAME
    export OS_PASSWORD=$TEST_PASSWORD
    export OS_PROJECT_DOMAIN_ID=$test_domain_id
    export OS_USER_DOMAIN_NAME=$TEST_USER_DOMAIN_NAME
    export OS_PROJECT_NAME=$TEST_PROJECT_NAME
    export OS_PROJECT_ID=$test_project_id
    env | grep OS_

    echo "Add wlm rc parameters to run_tempest.sh\n"
    sed -i "2i export OS_USERNAME=$TEST_USERNAME" run_tempest.sh
    sed -i "2i export OS_PASSWORD=$TEST_PASSWORD" run_tempest.sh
    sed -i "2i export OS_PROJECT_ID=$test_project_id" run_tempest.sh
    sed -i "2i export OS_USER_DOMAIN_NAME=$TEST_USER_DOMAIN_NAME" run_tempest.sh
    sed -i "2i export OS_PROJECT_DOMAIN_ID=$test_domain_id" run_tempest.sh
    sed -i "2i export OS_AUTH_URL=$AUTH_URL" run_tempest.sh
    sed -i "2i export OS_IDENTITY_API_VERSION=$IDENTITY_API_VERSION" run_tempest.sh
    sed -i "2i export OS_REGION_NAME=$REGION_NAME" run_tempest.sh
    sed -i "2i export OS_ENDPOINT_TYPE=$ENDPOINT_TYPE" run_tempest.sh
    sed -i "2i export OS_INTERFACE=$ENDPOINT_TYPE" run_tempest.sh
    sed -i "2i export OS_PROJECT_NAME=$TEST_PROJECT_NAME" run_tempest.sh

    # network
    ASSIGN_SUBNET () {
      subnet_id=`($OPENSTACK_CMD subnet list --network $1 | awk '$2 && $2 != "ID" {print $2}')`
      echo "subnet_id: "$subnet_id
      if [[ $subnet_id == "" ]]; then
         echo "Internal subnet not available, creating new subnet"
         $OPENSTACK_CMD subnet create --project $test_project_id --subnet-range 18.18.1.0/24 --dhcp --ip-version 4 --network $1 test_internal_subnet
      else
         echo "Internal subnet available"
      fi
    }

    ASSIGN_ROUTER () {
      subnet_id=`($OPENSTACK_CMD subnet list | grep $1 | awk '$2 && $2 != "ID" {print $2}')`
      
      # router
      ext_network_id=`($OPENSTACK_CMD network list --external --long -c ID -c "Router Type" | awk -F'|' '!/^(+--)|ID|aki|ari/ { print $2 }' | head -1)`
      if [ -z "$ext_network_id" ]; then
          echo "External network not available"
      fi
  
      while read -r ROUTER_UUID; do
              router_id="$ROUTER_UUID"
          routers+=($ROUTER_UUID)
      done < <($OPENSTACK_CMD router list --long -c ID --project $test_project_id | awk -F'|' '!/^(+--)|ID|aki|ari/ { print $2 }')
   
      case "${#routers[*]}" in
          0)
              echo "Found no routers to use! Creating new router\n"
              $OPENSTACK_CMD router create --enable --project $test_project_id test_router
              router_id=`($OPENSTACK_CMD router list --project $test_project_id | grep test_router | awk '$2 && $2 != "ID" {print $2}')`
              $OPENSTACK_CMD router set --external-gateway $ext_network_id $router_id
              $OPENSTACK_CMD router add subnet $router_id $subnet_id
              ;;
          *)
              echo "Found router to use!\n"
              if [ -z "$router_id" ]; then
                  router_id=${routers[0]}
              fi
              gateway_info=`($OPENSTACK_CMD router show $router_id | grep external_gateway_info | awk -F'|' '!/^(+--)|ID|aki|ari/ { print $3 }')`
              interface_info=`($OPENSTACK_CMD router show $router_id | grep interfaces_info | awk -F'|' '!/^(+--)|ID|aki|ari/ { print $3 }')`
              
              if [[ "$gateway_info" == *"None"* ]] | [ "$gateway_info" == "null" ]
              then
                  echo "External gateway not set"
                  output=$($OPENSTACK_CMD router set --external-gateway $ext_network_id $router_id 2>&1)
                  echo $output
                  if [[ $output =~ .*"No more IP addresses available".* ]]
                  then
                    echo "Relaesing Floating Ips and retry gateway creation"
                    floating_ip_cnt1=`$OPENSTACK_CMD floating ip list --project $test_project_id | awk -F'|' '!/^(+--)|ID|aki|ari/ { print $2 }' | wc -l`
                    if [ $floating_ip_cnt1 -le 1 ]
                    then
                      echo "ERROR Floating Ips insufficient"
                    else
                      floating_ip=`($OPENSTACK_CMD floating ip list --project $test_project_id | awk -F'|' '!/^(+--)|ID|aki|ari/ { print $2 }' | tail -1)`
                      $OPENSTACK_CMD floating ip delete ${floating_ip}
                      $OPENSTACK_CMD router set --external-gateway $ext_network_id $router_id
                    fi
                  elif [[ $output == *"Error"* ]]
                  then
                    echo "Gateway creation Failed with ERROR : " + $output
                  fi

              else
                  echo "External gateway already set"
              fi

              if [[ "$interface_info" == *"$subnet_id"* ]]
              then
                  echo "Internal interface already added to router"
              else
                  echo "Internal interface not added to router"
                  $OPENSTACK_CMD router add subnet $router_id $subnet_id
              fi
              ;;
      esac
    }
    
    
    echo "Fetch network information\n"
    while read -r NETWORK_TYPE NETWORK_UUID; do
        if [ "$NETWORK_TYPE" = "Internal" ]; then
            network_id="$NETWORK_UUID"    
            network_id_alt="$NETWORK_UUID"     
        fi
        networks+=($NETWORK_UUID)
    done < <($OPENSTACK_CMD network list --long -c ID -c "Router Type" --project $test_project_id | awk -F'|' '!/^(+--)|ID|aki|ari/ { print $3,$2 }')
 

    case "${#networks[*]}" in
        0)
            echo "Found no internal networks to use! Creating new internal network\n"
            $OPENSTACK_CMD network create --internal --enable --project $test_project_id test_internal_network
            network_id=`($OPENSTACK_CMD network list --project $test_project_id | grep test_internal_network | awk '$2 && $2 != "ID" {print $2}')`
            network_id_alt=$network_id
	    ASSIGN_SUBNET $network_id
            ASSIGN_ROUTER $network_id
            ;;
        1)
            echo "Found single internal network to use!\n"
            if [ -z "$network_id" ]; then
                network_id=${networks[0]}
                network_id_alt=${networks[0]}
            fi
	    ASSIGN_SUBNET $network_id
            ASSIGN_ROUTER $network_id
            ;;
        *)
            echo "Found multiple internal networks to use!\n"
            network_id=${networks[*]:0:1}
            network_id_alt=${networks[*]:1:1}
	    ASSIGN_SUBNET $network_id
	    ASSIGN_SUBNET $network_id_alt
            ASSIGN_ROUTER $network_id
            ASSIGN_ROUTER $network_id_alt
            ;;
    esac
    
    
    #Allocate floating ips to $TEST_PROJECT_NAME
    floating_ip_cnt=`$OPENSTACK_CMD floating ip list --project $test_project_id | awk -F'|' '!/^(+--)|ID|aki|ari/ { print $2 }' | wc -l`
    while [ $floating_ip_cnt -le 5 ]
    do
        $OPENSTACK_CMD floating ip create --project $test_project_id $ext_network_id
        floating_ip_cnt=$(( $floating_ip_cnt + 1 ))
    done
    $OPENSTACK_CMD floating ip list --project $test_project_id

    #Update default security group rules
    def_secgrp_id=`($OPENSTACK_CMD security group list --project $test_project_id | grep default | awk -F'|' '!/^(+--)|ID|aki|ari/ { print $2 }')`
    echo $def_secgrp_id
    $OPENSTACK_CMD security group show $def_secgrp_id
    $OPENSTACK_CMD security group rule create --ethertype IPv4 --ingress --protocol tcp --dst-port 1:65535 $def_secgrp_id
    $OPENSTACK_CMD security group rule create --ethertype IPv4 --egress --protocol tcp --dst-port 1:65535 $def_secgrp_id
    $OPENSTACK_CMD security group rule create --ethertype IPv4 --ingress --protocol icmp $def_secgrp_id
    $OPENSTACK_CMD security group rule create --ethertype IPv4 --egress --protocol icmp $def_secgrp_id
    
    iniset $TEMPEST_CONFIG network internal_network_id $network_id
    iniset $TEMPEST_CONFIG network alt_internal_network_id $network_id_alt
    iniset $TEMPEST_CONFIG network public_router_id $router_id

    # identity-feature-enabled
    iniset $TEMPEST_CONFIG identity-feature-enabled api_v2 False
    iniset $TEMPEST_CONFIG identity-feature-enabled api_v3 True

    # Dashboard
    controller_ip=`echo $OS_AUTH_URL | cut -d ':' -f2 | cut -d '/' -f3`
    login_url=http://$controller_ip/auth/login/
    dashboard_url=http://$controller_ip/
    
    iniset $TEMPEST_CONFIG dashboard login_url $login_url
    iniset $TEMPEST_CONFIG dashboard dashboard_url $dashboard_url

    # wlm
    iniset $TEMPEST_CONFIG wlm os_tenant_id $service_project_id

    # accounts.yaml
    sed -i '/tenant_name/c \  tenant_name: '\'$TEST_PROJECT_NAME\' $TEMPEST_ACCOUNTS
    sed -i '/username/c - username: '\'$TEST_USERNAME\' $TEMPEST_ACCOUNTS
    sed -i '/password/c \  password: '\'$TEST_PASSWORD\' $TEMPEST_ACCOUNTS
    sed -i '/domain_name/c \  domain_name: '\'$TEST_DOMAIN_NAME\' $TEMPEST_ACCOUNTS

    TEMP_IP=${TVAULT_IP}
    IP=""
    cnt=0
    IFS=' ' read -ra IP <<< "${TVAULT_IP[@]}"
    for i in "${IP[@]}"; do
       if [ $cnt -eq 0 ]
       then
          TVAULT_IP="[""\""$i"\""
       else
          TVAULT_IP+=", \""$i"\""
       fi
       cnt=`expr $cnt + 1`
    done
    TVAULT_IP+="]"


    #check for user name in TEST_IMAGE_NAME
    #keep TEST_USER_NAME value as "ubuntu" for the default case.
    #convert test image name to lower case for comparison...
    IMAGE_NAME=${TEST_IMAGE_NAME,,}
    case $IMAGE_NAME in
        *"ubuntu"*)
                search_pattern="ubuntu"
                res=${IMAGE_NAME#*$search_pattern}
                pos=$(( ${#IMAGE_NAME} - ${#res} - ${#search_pattern} ))
                TEST_USER_NAME=${TEST_IMAGE_NAME:$pos:${#search_pattern}}
		BOOTVOL_SIZE=10
                ;;
        *"centos"*)
                search_pattern="centos"
                res=${IMAGE_NAME#*$search_pattern}
                pos=$(( ${#IMAGE_NAME} - ${#res} - ${#search_pattern} ))
                TEST_USER_NAME=${TEST_IMAGE_NAME:$pos:${#search_pattern}}
		BOOTVOL_SIZE=10
                ;;
        *"cirros"*)
                search_pattern="cirros"
                res=${IMAGE_NAME#*$search_pattern}
                pos=$(( ${#IMAGE_NAME} - ${#res} - ${#search_pattern} ))
                TEST_USER_NAME=${TEST_IMAGE_NAME:$pos:${#search_pattern}}
		BOOTVOL_SIZE=4
                ;;
        *)
                TEST_USER_NAME="ubuntu"
		BOOTVOL_SIZE=10
                ;;
    esac


    # tvaultconf.py
    sed -i '/tvault_ip/d' $TEMPEST_TVAULTCONF
    echo 'tvault_ip='$TVAULT_IP'' >> $TEMPEST_TVAULTCONF
    sed -i '/no_of_compute_nodes = /c no_of_compute_nodes = '$no_of_computes'' $TEMPEST_TVAULTCONF
    sed -i '/enabled_tests = /c enabled_tests = '$enabled_tests'' $TEMPEST_TVAULTCONF
    sed -i '/instance_username = /c instance_username = "'$TEST_USER_NAME'"' $TEMPEST_TVAULTCONF
    sed -i '/bootfromvol_vol_size = /c bootfromvol_vol_size = '$BOOTVOL_SIZE'' $TEMPEST_TVAULTCONF
    sed -i '/tvault_dbname = /c tvault_dbname = "'$dbname'"' $TEMPEST_TVAULTCONF
    sed -i '/wlm_dbusername = /c wlm_dbusername = "'$dbusername'"' $TEMPEST_TVAULTCONF
    sed -i '/wlm_dbpasswd = /c wlm_dbpasswd = "'$mysql_wlm_pwd'"' $TEMPEST_TVAULTCONF
    sed -i '/wlm_dbhost = /c wlm_dbhost = "'$mysql_ip'"' $TEMPEST_TVAULTCONF
    sed -i "/user_frm_data = /c user_frm_data = \"$TEMPEST_FRM_FILE\"" $TEMPEST_TVAULTCONF
    sed -i '/tvault_version = /c tvault_version = "'$tvault_version'"' $TEMPEST_TVAULTCONF
    sed -i '/trustee_role = /c trustee_role = "'$TRUSTEE_ROLE'"' $TEMPEST_TVAULTCONF

}


if [ -d $OPENSTACK_CLI_VENV ]
then
   rm -rf $OPENSTACK_CLI_VENV
fi

echo "creating virtual env for openstack client"
python$PYTHON_VERSION -m venv $OPENSTACK_CLI_VENV

. $OPENSTACK_CLI_VENV/bin/activate
source openstack-setup.conf
pip$PYTHON_VERSION install wheel
pip$PYTHON_VERSION install --upgrade pip
pip$PYTHON_VERSION install openstacksdk
pip$PYTHON_VERSION install os-client-config
pip$PYTHON_VERSION install python-openstackclient

configure_tempest
deactivate
echo "cleaning up openstack client virtual env"
rm -rf $OPENSTACK_CLI_VENV
