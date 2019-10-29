#!/bin/bash -x
source openstack-setup.conf

TEMPEST_DIR=$PWD
TEMPEST_CONFIG_DIR=${TEMPEST_CONFIG_DIR:-$TEMPEST_DIR/etc}
TEMPEST_CONFIG=$TEMPEST_CONFIG_DIR/tempest.conf
TEMPEST_STATE_PATH=${TEMPEST_CONFIG_DIR:-$TEMPEST_DIR/lock}
TEMPEST_ACCOUNTS=$TEMPEST_CONFIG_DIR/accounts.yaml
TEMPEST_TVAULTCONF=$TEMPEST_DIR/tempest/tvaultconf.py
OPENSTACK_CLI_VENV=$TEMPEST_DIR/.myenv
git checkout run_tempest.sh

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
    else
        iniset $TEMPEST_CONFIG identity disable_ssl_certificate_validation False
        iniset $TEMPEST_CONFIG wlm insecure False
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
    export OS_TENANT_ID=$CLOUDADMIN_PROJECT_ID
    export OS_AUTH_URL=$AUTH_URL
    export OS_IDENTITY_API_VERSION=$IDENTITY_API_VERSION
    export OS_REGION_NAME=$REGION_NAME
    export OS_ENDPOINT_TYPE=$ENDPOINT_TYPE
    export OS_INTERFACE=$ENDPOINT_TYPE

    admin_domain_id=$($OPENSTACK_CMD domain list | awk "/ $CLOUDADMIN_DOMAIN_NAME / { print \$2 }")
    test_domain_id=$($OPENSTACK_CMD domain list | awk "/ $TEST_DOMAIN_NAME / { print \$2 }")
    test_project_id=$($OPENSTACK_CMD project list | awk "/ $TEST_PROJECT_NAME / { print \$2 }")
    test_alt_project_id=$($OPENSTACK_CMD project list | awk "/ $TEST_ALT_PROJECT_NAME / { print \$2 }")
    service_project_id=$($OPENSTACK_CMD project list | awk "/service*/ { print \$2 }")
    wlm_endpoint=$($OPENSTACK_CMD endpoint list |  awk "/workloads/" | awk "/public/ { print \$14 }")
    if [[ "$wlm_endpoint" =~ "https" ]]
    then
        git checkout tempest/command_argument_string.py
        sed -i 's/workloadmgr /workloadmgr --insecure /g' tempest/command_argument_string.py
        iniset $TEMPEST_CONFIG wlm insecure True
    fi
    
    # Glance should already contain images to be used in tempest
    # testing. Here we simply look for images stored in Glance
    # and set the appropriate variables for use in the tempest config
    # We ignore ramdisk and kernel images, look for the default image
    # ``TEST_IMAGE_NAME``. If not found, we set the ``image_uuid`` to the
    # first image returned and set ``image_uuid_alt`` to the second,
    # if there is more than one returned...
    # ... Also ensure we only take active images, so we don't get snapshots in process
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
        $OPENSTACK_CMD flavor create --ram 4096 --disk 40 --vcpus 2 $FVM_IMAGE_NAME
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

    compute_az=$($OPENSTACK_CMD availability zone list --long | awk "/ nova-compute / " | awk "/ available / { print \$2 }")
    no_of_computes=$($OPENSTACK_CMD compute service list | awk "/ nova-compute / " | wc -l)

    iniset $TEMPEST_CONFIG compute image_ref $image_uuid
    iniset $TEMPEST_CONFIG compute fvm_image_ref $fvm_image_uuid
    iniset $TEMPEST_CONFIG compute flavor_ref $flavor_ref
    iniset $TEMPEST_CONFIG compute flavor_ref_alt $flavor_ref_alt
    iniset $TEMPEST_CONFIG compute vm_availability_zone $compute_az

    # Volume
    echo "Fetching volume type details\n"
    volume_az=$($OPENSTACK_CMD availability zone list --volume | awk "/ available / { print \$2 }")
    case "${#CINDER_BACKENDS_ENABLED[*]}" in
        0)
            echo "No volume type available to use!\n"
            exit 1
            ;;
        1)
            type=${CINDER_BACKENDS_ENABLED[0]}
            type_id=$($OPENSTACK_CMD volume type list | grep $type | awk '$2 && $2 != "ID" {print $2}')
            volume_type=$type
            volume_type_id=$type_id
            enabled_tests=[\"Attached_Volume_"$volume_type\"",\"Boot_from_Volume_"$volume_type\""]
            ;;
        *)
            cnt=0
            for type in ${CINDER_BACKENDS_ENABLED[@]}; do
                type_id=$($OPENSTACK_CMD volume type list | grep $type | awk '$2 && $2 != "ID" {print $2}')
                case $type in
                    lvm*|iscsi*) volume_type_alt=$type
                                 volume_type_id_alt=$($OPENSTACK_CMD volume type list | grep $type | awk '$2 && $2 != "ID" {print $2}');;
                    *) volume_type=$type
                       volume_type_id=$($OPENSTACK_CMD volume type list | grep $type | awk '$2 && $2 != "ID" {print $2}');;
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
    iniset $TEMPEST_CONFIG identity admin_domain_name $CLOUDADMIN_DOMAIN_NAME
    iniset $TEMPEST_CONFIG identity admin_domain_id $admin_domain_id
    iniset $TEMPEST_CONFIG identity admin_tenant_id $CLOUDADMIN_PROJECT_ID
    iniset $TEMPEST_CONFIG identity admin_tenant_name $CLOUDADMIN_PROJECT_NAME
    iniset $TEMPEST_CONFIG identity admin_password $CLOUDADMIN_PASSWORD
    iniset $TEMPEST_CONFIG identity admin_username $CLOUDADMIN_USERNAME
    iniset $TEMPEST_CONFIG identity tenant_name $TEST_PROJECT_NAME
    iniset $TEMPEST_CONFIG identity password $TEST_PASSWORD
    iniset $TEMPEST_CONFIG identity username $TEST_USERNAME
    iniset $TEMPEST_CONFIG identity tenant_id $test_project_id
    iniset $TEMPEST_CONFIG identity tenant_id_1 $test_alt_project_id
    iniset $TEMPEST_CONFIG identity domain_id $test_domain_id
    iniset $TEMPEST_CONFIG identity default_domain_id $test_domain_id
    iniset $TEMPEST_CONFIG identity uri_v3 $OS_AUTH_URL
    iniset $TEMPEST_CONFIG identity v3_endpoint_type $ENDPOINT_TYPE
    iniset $TEMPEST_CONFIG identity region $OS_REGION_NAME

    # Auth
    iniset $TEMPEST_CONFIG auth use_dynamic_credentials False
    iniset $TEMPEST_CONFIG auth test_accounts_file $TEMPEST_ACCOUNTS
    iniset $TEMPEST_CONFIG auth allow_tenant_isolation True

    #Set test user credentials
    echo "Set test user credentials\n"
    export OS_USERNAME=$TEST_USERNAME
    export OS_PASSWORD=$TEST_PASSWORD
    export OS_PROJECT_DOMAIN_NAME=$TEST_DOMAIN_NAME
    export OS_USER_DOMAIN_NAME=$TEST_USER_DOMAIN_NAME
    export OS_PROJECT_NAME=$TEST_PROJECT_NAME
    export OS_TENANT_ID=$test_project_id

    echo "Add wlm rc parameters to run_tempest.sh\n"
    sed -i "2i export OS_USERNAME=$TEST_USERNAME" run_tempest.sh
    sed -i "2i export OS_PASSWORD=$TEST_PASSWORD" run_tempest.sh
    sed -i "2i export OS_TENANT_ID=$test_project_id" run_tempest.sh
    sed -i "2i export OS_DOMAIN_ID=$test_domain_id" run_tempest.sh
    sed -i "2i export OS_AUTH_URL=$AUTH_URL" run_tempest.sh
    sed -i "2i export OS_IDENTITY_API_VERSION=$IDENTITY_API_VERSION" run_tempest.sh
    sed -i "2i export OS_REGION_NAME=$REGION_NAME" run_tempest.sh
    sed -i "2i export OS_ENDPOINT_TYPE=$ENDPOINT_TYPE" run_tempest.sh
    sed -i "2i export OS_INTERFACE=$ENDPOINT_TYPE" run_tempest.sh

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
    while read -r NETWORK_TYPE NETWORK_UUID; do
        if [ "$NETWORK_TYPE" = "External" ]; then
            ext_network_id="$NETWORK_UUID"
        fi
        networks+=($NETWORK_UUID)
    done < <($OPENSTACK_CMD network list --long -c ID -c "Router Type" | awk -F'|' '!/^(+--)|ID|aki|ari/ { print $3,$2 }')

    while read -r ROUTER_UUID; do
            router_id="$ROUTER_UUID"
        routers+=($ROUTER_UUID)
    done < <($OPENSTACK_CMD router list --long -c ID --project $test_project_id | awk -F'|' '!/^(+--)|ID|aki|ari/ { print $2 }')
    
    case "${#routers[*]}" in
        0)
            echo "Found no routers to use! Creating new router\n"
            $OPENSTACK_CMD router create --enable --project $test_project_id test_router
            router_id=`($OPENSTACK_CMD router list | grep test_router | awk '$2 && $2 != "ID" {print $2}')`
            $OPENSTACK_CMD router set --external-gateway $ext_network_id test_router
            $OPENSTACK_CMD router add subnet test_router test_internal_subnet
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

    # tvaultconf.py
    sed -i '/tvault_ip = /c tvault_ip = "'$TVAULT_IP'"' $TEMPEST_TVAULTCONF
    sed -i '/no_of_compute_nodes = /c no_of_compute_nodes = '$no_of_computes'' $TEMPEST_TVAULTCONF
    sed -i '/enabled_tests = /c enabled_tests = '$enabled_tests'' $TEMPEST_TVAULTCONF
    sed -i '/instance_username = /c instance_username = "'$TEST_IMAGE_NAME'"' $TEMPEST_TVAULTCONF

}


if [ -d $OPENSTACK_CLI_VENV ]
then
   rm -rf $OPENSTACK_CLI_VENV
fi

echo "creating virtual env for openstack client"
virtualenv $OPENSTACK_CLI_VENV
. $OPENSTACK_CLI_VENV/bin/activate
pip install openstacksdk==0.35.0
pip install os-client-config==1.18.0
pip install python-openstackclient==3.19.0
pip install python-cinderclient==4.2.0

configure_tempest
deactivate
echo "cleaning up openstack client virtual env"
#rm -rf $OPENSTACK_CLI_VENV
