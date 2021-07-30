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
NONADMIN_USERNAME=trilio-nonadmin-user
NONADMIN_PWD=password
NEWADMIN_USERNAME=trilio-newadmin-user
NEWADMIN_PWD=password
BACKUP_USERNAME=trilio-backup-user
BACKUP_PWD=password
git checkout run_tempest.sh

sed -i "2i export PYTHON_VERSION=$PYTHON_VERSION" run_tempest.sh
sed -i "/PYTHON_CMD=/c PYTHON_CMD=\"python$PYTHON_VERSION\"" sanity-run.sh
sed -i "/PYTHON_CMD=/c PYTHON_CMD=\"python$PYTHON_VERSION\"" master-run.sh

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
    $OPENSTACK_CMD role add --user $NONADMIN_USERNAME --user-domain $TEST_DOMAIN_NAME --project $TEST_PROJECT_NAME $TRUSTEE_ROLE
    $OPENSTACK_CMD role add --user $NONADMIN_USERNAME --user-domain $TEST_DOMAIN_NAME --project $TEST_ALT_PROJECT_NAME $TRUSTEE_ROLE
    $OPENSTACK_CMD role add --user $NEWADMIN_USERNAME --user-domain $TEST_DOMAIN_NAME --project $TEST_PROJECT_NAME $TRUSTEE_ROLE
    $OPENSTACK_CMD role add --user $NEWADMIN_USERNAME --user-domain $TEST_DOMAIN_NAME --project $TEST_PROJECT_NAME newadmin
    $OPENSTACK_CMD role add --user $BACKUP_USERNAME --user-domain $TEST_DOMAIN_NAME --project $TEST_PROJECT_NAME $TRUSTEE_ROLE
    $OPENSTACK_CMD role add --user $BACKUP_USERNAME --user-domain $TEST_DOMAIN_NAME --project $TEST_PROJECT_NAME backup

    #Fetch identity data
    admin_domain_id=$($OPENSTACK_CMD domain list | awk "/ $CLOUDADMIN_DOMAIN_NAME / { print \$2 }")
    test_domain_id=$($OPENSTACK_CMD domain list | awk "/ $TEST_DOMAIN_NAME / { print \$2 }")
    test_project_id=$($OPENSTACK_CMD project list | awk "/ $TEST_PROJECT_NAME / { print \$2 }")
    test_alt_project_id=$($OPENSTACK_CMD project list | awk "/ $TEST_ALT_PROJECT_NAME / { print \$2 }")
    service_project_id=$($OPENSTACK_CMD project list | awk "/service*/ { print \$2 }")
    test_user_id=$($OPENSTACK_CMD user list --domain $TEST_DOMAIN_NAME | awk "/ $TEST_USERNAME / { print \$2 }")
    test_alt_user_id=$($OPENSTACK_CMD user list --domain $TEST_DOMAIN_NAME | awk "/ $NONADMIN_USERNAME / { print \$2 }")
    wlm_endpoint=$($OPENSTACK_CMD endpoint list |  awk "/workloads/" | awk "/public/ { print \$14 }")

    unset OS_PROJECT_DOMAIN_NAME
    export OS_PROJECT_DOMAIN_ID=$admin_domain_id

    if [[ "$wlm_endpoint" =~ "https" ]]
    then
        git checkout tempest/command_argument_string.py
        sed -i 's/workloadmgr /workloadmgr --insecure /g' tempest/command_argument_string.py
        iniset $TEMPEST_CONFIG wlm insecure True
    fi
    
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

    #Check if File recovery manager image is already available. If not, create the image
    fvm_image_uuid=`$OPENSTACK_CMD image list | grep $FVM_IMAGE_NAME | cut -d '|' -f2`
    if [[ -z $fvm_image_uuid ]]
    then
        echo "File recovery manager instance not available\n"
    fi

    echo "Fetching flavor details\n"
    available_flavors=$($OPENSTACK_CMD flavor list)
    if [[ ! ( $available_flavors =~ $TEST_IMAGE_NAME ) ]] ; then
        if [[ $TEST_IMAGE_NAME =~ "cirros" ]] ; then
            $OPENSTACK_CMD flavor create --ram 64 --disk 1 --vcpus 1 $TEST_IMAGE_NAME
        else
            $OPENSTACK_CMD flavor create --ram 4096 --disk 20 --vcpus 2 $TEST_IMAGE_NAME
        fi
    fi
    if [[ ! ( $available_flavors =~ $FVM_IMAGE_NAME ) ]] && [[ "$fvm_image_uuid" ]]; then
        # Determine the flavor disk size based on the image size.
        $OPENSTACK_CMD flavor create --ram 2048 --disk 14 --vcpus 2 $FVM_IMAGE_NAME
    fi
    available_flavors=$($OPENSTACK_CMD flavor list)
    IFS=$'\r\n'
    flavors=""
    fvm_flavor=""
    for line in $available_flavors; do
        f=$(echo $line | awk "/ $TEST_IMAGE_NAME / { print \$2 }")
        flavors="$flavors $f"
        f1=$(echo $line | awk "/ $FVM_IMAGE_NAME / { print \$2 }")
        fvm_flavor="$fvm_flavor $f1"
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

    compute_az=$($OPENSTACK_CMD availability zone list --long | awk "/ nova-compute / " | awk "/ available / { print \$2 }" | head -1)
    no_of_computes=$($OPENSTACK_CMD compute service list | awk "/ nova-compute / " | wc -l)

    iniset $TEMPEST_CONFIG compute image_ref $image_uuid
    iniset $TEMPEST_CONFIG compute fvm_image_ref $fvm_image_uuid
    iniset $TEMPEST_CONFIG compute flavor_ref $flavor_ref
    iniset $TEMPEST_CONFIG compute flavor_ref_alt $flavor_ref_alt
    iniset $TEMPEST_CONFIG compute vm_availability_zone $compute_az

    # Volume
    echo "Fetching volume type details\n"
    volume_az=$($OPENSTACK_CMD availability zone list --volume | awk "/ available / { print \$2 }")
    shopt -s nocasematch
    case "${#CINDER_BACKENDS_ENABLED[*]}" in
        0)
            echo "No volume type available to use, using Default \n"
            type="ceph"
            type_id=$($OPENSTACK_CMD volume type list | grep DEFAULT | awk '$2 && $2 != "ID" {print $2}')
            volume_type=$type
            volume_type_id=$type_id
            enabled_tests=[\"Attached_Volume_"$volume_type\"",\"Boot_from_Volume_"$volume_type\""]
            ;;
        1)
            type=${CINDER_BACKENDS_ENABLED[0]}
            type_id=$($OPENSTACK_CMD volume type list | grep -i $type | awk '$2 && $2 != "ID" {print $2}' | head -1)
            volume_type=$type
            volume_type_id=$type_id
            volume_type_alt=$type
            volume_type_id_alt=$type_id
            enabled_tests=[\"Attached_Volume_"$volume_type\"",\"Boot_from_Volume_"$volume_type\""]
            ;;
        *)
            cnt=0
            for type in ${CINDER_BACKENDS_ENABLED[@]}; do
                type_id=$($OPENSTACK_CMD volume type list | grep -i $type | awk '$2 && $2 != "ID" {print $2}')
                case $type in
                    lvm*|iscsi*) volume_type_alt=$type
                                 volume_type_id_alt=$($OPENSTACK_CMD volume type list | grep -i $type | awk '$2 && $2 != "ID" {print $2}');;
                    *) volume_type=$type
                       volume_type_id=$($OPENSTACK_CMD volume type list | grep -i $type | awk '$2 && $2 != "ID" {print $2}');;
                esac
                if [ $cnt -eq 0 ]
                then
                    enabled_tests=[\"Attached_Volume_"$type\"",\"Boot_from_Volume_"$type\""
                else
                    enabled_tests+=,\"Attached_Volume_"$type\"",\"Boot_from_Volume_"$type\""]
                fi
                cnt+=1
            done
    esac

    iniset $TEMPEST_CONFIG volume volume_availability_zone $volume_az
    iniset $TEMPEST_CONFIG volume volume_type $volume_type
    iniset $TEMPEST_CONFIG volume volume_type_id $volume_type_id
    iniset $TEMPEST_CONFIG volume volume_type_1 $volume_type_alt
    iniset $TEMPEST_CONFIG volume volume_type_id_1 $volume_type_id_alt
    iniset $TEMPEST_CONFIG volume volume_size $VOLUME_SIZE

    # Identity
    iniset $TEMPEST_CONFIG identity auth_version v3
    iniset $TEMPEST_CONFIG identity admin_domain_id $admin_domain_id
    iniset $TEMPEST_CONFIG identity admin_tenant_id $CLOUDADMIN_PROJECT_ID
    iniset $TEMPEST_CONFIG identity tenant_name $TEST_PROJECT_NAME
    iniset $TEMPEST_CONFIG identity password $TEST_PASSWORD
    iniset $TEMPEST_CONFIG identity username $TEST_USERNAME
    iniset $TEMPEST_CONFIG identity project_name $TEST_PROJECT_NAME
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
    echo $conn_str
    dbusername=`echo $conn_str | cut -d '/' -f 3 | cut -d ':' -f 1`
    mysql_wlm_pwd=`echo $conn_str | cut -d '/' -f 3 | cut -d ':' -f 2 | cut -d '@' -f 1`
    mysql_ip=`echo $conn_str | cut -d '/' -f 3 | cut -d ':' -f 2 | cut -d '@' -f 2`
    dbname=`echo $conn_str | cut -d '/' -f 4 | cut -d '?' -f1`
    tvault_version=`workloadmgr --insecure workload-type-show Serial -f yaml | grep version | cut -d ':' -f2 | xargs`

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
            network_id=`($OPENSTACK_CMD network list | grep test_internal_network | awk '$2 && $2 != "ID" {print $2}')`
            network_id_alt=$network_id
            $OPENSTACK_CMD subnet create --project $test_project_id --subnet-range 16.16.1.0/24 --dhcp --ip-version 4 --network $network_id test_internal_subnet
;;
        1)
            if [ -z "$network_id" ]; then
                network_id=${networks[0]}
                network_id_alt=${networks[0]}
            fi
            ;;
        *)
            if [ -z "$network_id" ]; then
                network_id=${networks[0]}
                network_id_alt=${networks[1]}
            fi
            ;;
    esac

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
            router_id=`($OPENSTACK_CMD router list | grep test_router | awk '$2 && $2 != "ID" {print $2}')`
            subnet_id=`($OPENSTACK_CMD subnet list | grep $network_id | awk '$2 && $2 != "ID" {print $2}')`
            $OPENSTACK_CMD router set --external-gateway $ext_network_id test_router
            $OPENSTACK_CMD router add subnet test_router $subnet_id
            ;;
        1)
            if [ -z "$router_id" ]; then
                router_id=${routers[0]}
            fi
            ;;
        *)
            if [ -z "$router_id" ]; then
                router_id=${routers[0]}
            fi
            ;;
    esac
   
    #Allocate floating ips to $TEST_PROJECT_NAME
    floating_ip_cnt=`$OPENSTACK_CMD floating ip list --project $test_project_id | awk -F'|' '!/^(+--)|ID|aki|ari/ { print $2 }' | wc -l`
    while [ $floating_ip_cnt -le 5 ]
    do
        $OPENSTACK_CMD floating ip create $ext_network_id
        floating_ip_cnt=$(( $floating_ip_cnt + 1 ))
    done
    $OPENSTACK_CMD floating ip list

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

    if ! hash juju; then
        echo "juju is not installed"
	juju=0
    else
        echo "juju is installed"
	juju=1
    fi

    dbname="workloadmgr"
    if [ $juju == 1 ]; then
        modelname="controller"
        dbusername="workloadmgr"

        echo "fetch mysql root password"
        mysql_root_pwd=`juju run -m ${modelname} --unit mysql/leader 'leader-get root-password'`

        echo "fetch workloadmgr mysql connection details"
        mysql_wlm_pwd=`juju run -m ${modelname} --unit mysql/leader 'leader-get mysql-workloadmgr.passwd'`
	mysql_ip=`juju run -m ${modelname} --unit trilio-wlm/0 "grep 'sql_connection' /etc/workloadmgr/workloadmgr.conf | cut -d '/' -f 3 | cut -d '@' -f 2"`

        echo "Provide required access to connect to wlm database from maas node"
        cur_ip=`hostname -I | awk '{print $1}'`

        cat > /tmp/trilio-test.sh <<-EOF
mysql -u root -p${mysql_root_pwd} -e "GRANT ALL PRIVILEGES ON ${dbname}.* TO '${dbusername}'@'${cur_ip}' IDENTIFIED BY '${mysql_wlm_pwd}'"
EOF

        juju scp /tmp/trilio-test.sh mysql/0:/tmp/
        rm -f /tmp/trilio-test.sh
        juju run -m ${modelname} --unit mysql/0 "cat /tmp/trilio-test.sh"
        juju run -m ${modelname} --unit mysql/0 "bash /tmp/trilio-test.sh"
    else
        conn_str=`workloadmgr setting-list --insecure --get_hidden True -f value | grep sql_connection`
        dbusername=`echo $conn_str | cut -d '/' -f 3 | cut -d ':' -f 1`           
        mysql_wlm_pwd=`echo $conn_str | cut -d '/' -f 3 | cut -d ':' -f 2 | cut -d '@' -f 1`
        mysql_ip=`echo $conn_str | cut -d '/' -f 3 | cut -d ':' -f 2 | cut -d '@' -f 2`
        dbname=`echo $conn_str | cut -d '/' -f 4 | cut -d '?' -f1`
    fi

    # tvaultconf.py
    sed -i '/tvault_ip/d' $TEMPEST_TVAULTCONF
    echo 'tvault_ip='$TVAULT_IP'' >> $TEMPEST_TVAULTCONF
    sed -i '/no_of_compute_nodes = /c no_of_compute_nodes = '$no_of_computes'' $TEMPEST_TVAULTCONF
    sed -i '/enabled_tests = /c enabled_tests = '$enabled_tests'' $TEMPEST_TVAULTCONF
    sed -i '/instance_username = /c instance_username = "'$TEST_IMAGE_NAME'"' $TEMPEST_TVAULTCONF
    sed -i '/tvault_dbname = /c tvault_dbname = "'$dbname'"' $TEMPEST_TVAULTCONF
    sed -i '/wlm_dbusername = /c wlm_dbusername = "'$dbusername'"' $TEMPEST_TVAULTCONF
    sed -i '/wlm_dbpasswd = /c wlm_dbpasswd = "'$mysql_wlm_pwd'"' $TEMPEST_TVAULTCONF
    sed -i '/wlm_dbhost = /c wlm_dbhost = "'$mysql_ip'"' $TEMPEST_TVAULTCONF
    sed -i "/user_frm_data = /c user_frm_data = \"$TEMPEST_FRM_FILE\"" $TEMPEST_TVAULTCONF
    sed -i '/tvault_version = /c tvault_version = "'$tvault_version'"' $TEMPEST_TVAULTCONF

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
