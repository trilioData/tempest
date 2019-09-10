#!/bin/bash

ADMIN_USERNAME=cloudadmin
ADMIN_PASSWORD=Password1!
ADMIN_DOMAIN_NAME=clouddomain
ADMIN_USER_DOMAIN_NAME=clouddomain
ADMIN_PROJECT_NAME=cloudproject
ADMIN_PROJECT_ID=d03cb88119fb40d7977b105e33886be2
TEST_USERNAME=triliouser2
TEST_PASSWORD=password
TEST_DOMAIN_NAME=triliodomain1
TEST_USER_DOMAIN_NAME=triliodomain1
TEST_PROJECT_NAME=trilioproject1
TEST_ALT_PROJECT_NAME=trilioproject2
AUTH_URL=http://192.168.6.100:5000/v3
REGION_NAME=TestRegion
IDENTITY_API_VERSION=3

DEFAULT_IMAGE_NAME=cirros
DEFAULT_VOLUME_SIZE=1
CINDER_BACKENDS_ENABLED=(ceph iscsi)
DEFAULT_ENDPOINT_TYPE=publicURL

TEMPEST_DIR=$PWD
TEMPEST_CONFIG_DIR=${TEMPEST_CONFIG_DIR:-$TEMPEST_DIR/etc}
TEMPEST_CONFIG=$TEMPEST_CONFIG_DIR/tempest.conf
TEMPEST_STATE_PATH=${TEMPEST_STATE_PATH:=/opt/lock}
TEMPEST_ACCOUNTS=$TEMPEST_CONFIG_DIR/accounts.yaml
OPENSTACK_CLI_VENV=$TEMPEST_DIR/.myenv

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
    export OS_USERNAME=$ADMIN_USERNAME
    export OS_PASSWORD=$ADMIN_PASSWORD
    export OS_PROJECT_DOMAIN_NAME=$ADMIN_DOMAIN_NAME
    export OS_USER_DOMAIN_NAME=$ADMIN_USER_DOMAIN_NAME
    export OS_PROJECT_NAME=$ADMIN_PROJECT_NAME
    export OS_TENANT_ID=$ADMIN_PROJECT_ID
    export OS_AUTH_URL=$AUTH_URL
    export OS_IDENTITY_API_VERSION=$IDENTITY_API_VERSION
    export OS_REGION_NAME=$REGION_NAME
    export OS_ENDPOINT_TYPE=$DEFAULT_ENDPOINT_TYPE
    export OS_INTERFACE=$DEFAULT_ENDPOINT_TYPE

    admin_domain_id=$($OPENSTACK_CMD domain list | awk "/ $ADMIN_DOMAIN_NAME / { print \$2 }")
    test_domain_id=$($OPENSTACK_CMD domain list | awk "/ $TEST_DOMAIN_NAME / { print \$2 }")
    test_project_id=$($OPENSTACK_CMD project list | awk "/ $TEST_PROJECT_NAME / { print \$2 }")
    test_alt_project_id=$($OPENSTACK_CMD project list | awk "/ $TEST_ALT_PROJECT_NAME / { print \$2 }")
    service_project_id=$($OPENSTACK_CMD project list | awk "/service*/ { print \$2 }")
 

    # Glance should already contain images to be used in tempest
    # testing. Here we simply look for images stored in Glance
    # and set the appropriate variables for use in the tempest config
    # We ignore ramdisk and kernel images, look for the default image
    # ``DEFAULT_IMAGE_NAME``. If not found, we set the ``image_uuid`` to the
    # first image returned and set ``image_uuid_alt`` to the second,
    # if there is more than one returned...
    # ... Also ensure we only take active images, so we don't get snapshots in process
    declare -a images

    while read -r IMAGE_NAME IMAGE_UUID; do
        if [ "$IMAGE_NAME" = "$DEFAULT_IMAGE_NAME" ]; then
            image_uuid="$IMAGE_UUID"
            image_uuid_alt="$IMAGE_UUID"
        fi
        images+=($IMAGE_UUID)
    done < <($OPENSTACK_CMD image list --property status=active | awk -F'|' '!/^(+--)|ID|aki|ari/ { print $3,$2 }')

    case "${#images[*]}" in
        0)
            echo "Found no valid images to use!"
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
    fvm_image_uuid=`$OPENSTACK_CMD image list | grep fvm | cut -d '|' -f2`
    if [[ -z $fvm_image_uuid ]]
    then
        echo "File recovery manager instance not available, exiting\n"
        exit 1
    fi

    # Compute
    # If ``DEFAULT_INSTANCE_TYPE`` is not declared, use the new behavior
    # Tempest creates its own instance types
      available_flavors=$($OPENSTACK_CMD flavor list)
    if  [[ -z "$DEFAULT_INSTANCE_TYPE" ]]; then
        if [[ ! ( $available_flavors =~ 'm1.nano' ) ]]; then
            # Determine the flavor disk size based on the image size.
            disk=$(image_size_in_gib $image_uuid)
            $OPENSTACK_CMD flavor create --id 42 --ram 64 --disk $disk --vcpus 1 m1.nano
        fi
        flavor_ref_alt=45
        if [[ ! ( $available_flavors =~ 'm1.fvm' ) ]]; then
            # Determine the flavor disk size based on the image size.
            disk_fvm=$(image_size_in_gib $fvm_image_uuid)
            $OPENSTACK_CMD flavor create --id 45 --ram 4096 --disk $disk_fvm --vcpus 2 m1.fvm
        fi
        flavor_ref=42
    else
        # Check Nova for existing flavors, if ``DEFAULT_INSTANCE_TYPE`` is set use it.
        IFS=$'\r\n'
        flavors=""
        for line in $available_flavors; do
            f=$(echo $line | awk "/ $DEFAULT_INSTANCE_TYPE / { print \$2 }")
            flavors="$flavors $f"
        done

        for line in $available_flavors; do
            flavors="$flavors `echo $line | grep -v "^\(|\s*ID\|+--\)" | cut -d' ' -f2`"
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
    fi
    compute_az=$($OPENSTACK_CMD availability zone list --long | awk "/ nova-compute / " | awk "/ available / { print \$2 }")

    iniset $TEMPEST_CONFIG compute image_ref $image_uuid
    iniset $TEMPEST_CONFIG compute fvm_image_ref $fvm_image_uuid
    iniset $TEMPEST_CONFIG compute flavor_ref $flavor_ref
    iniset $TEMPEST_CONFIG compute flavor_ref_alt $flavor_ref_alt
    iniset $TEMPEST_CONFIG compute vm_availability_zone $compute_az

    # Volume
    volume_az=$($OPENSTACK_CMD availability zone list --volume | awk "/ available / { print \$2 }")
    case "${#CINDER_BACKENDS_ENABLED[*]}" in
        0)
            echo "No volume type available to use!"
            exit 1
            ;;
        1)
            type=${CINDER_BACKENDS_ENABLED[0]}
            type_id=$($OPENSTACK_CMD volume type list | grep $type | awk '$2 && $2 != "ID" {print $2}')
            volume_type=$type
            volume_type_id=$type_id
            ;;
        *)
            for type in ${CINDER_BACKENDS_ENABLED[@]}; do
                type_id=$($OPENSTACK_CMD volume type list | grep $type | awk '$2 && $2 != "ID" {print $2}')
                case $type in
                    lvm*|iscsi*) volume_type_alt=$type
                                 volume_type_id_alt=$($OPENSTACK_CMD volume type list | grep $type | awk '$2 && $2 != "ID" {print $2}');;
                    *) volume_type=$type
                       volume_type_id=$($OPENSTACK_CMD volume type list | grep $type | awk '$2 && $2 != "ID" {print $2}');;
                esac
            done
    esac

    iniset $TEMPEST_CONFIG volume volume_availability_zone $volume_az
    iniset $TEMPEST_CONFIG volume volume_type $volume_type
    iniset $TEMPEST_CONFIG volume volume_type_id $volume_type_id
    iniset $TEMPEST_CONFIG volume volume_type_1 $volume_type_alt
    iniset $TEMPEST_CONFIG volume volume_type_id_1 $volume_type_id_alt
    iniset $TEMPEST_CONFIG volume volume_size $DEFAULT_VOLUME_SIZE

    # Identity
    iniset $TEMPEST_CONFIG identity auth_version v3
    iniset $TEMPEST_CONFIG identity admin_domain_name $ADMIN_DOMAIN_NAME
    iniset $TEMPEST_CONFIG identity admin_domain_id $admin_domain_id
    iniset $TEMPEST_CONFIG identity admin_tenant_id $ADMIN_PROJECT_ID
    iniset $TEMPEST_CONFIG identity admin_tenant_name $ADMIN_PROJECT_NAME
    iniset $TEMPEST_CONFIG identity admin_password $ADMIN_PASSWORD
    iniset $TEMPEST_CONFIG identity admin_username $ADMIN_USERNAME
    iniset $TEMPEST_CONFIG identity tenant_name $TEST_PROJECT_NAME
    iniset $TEMPEST_CONFIG identity password $TEST_PASSWORD
    iniset $TEMPEST_CONFIG identity username $TEST_USERNAME
    iniset $TEMPEST_CONFIG identity tenant_id $test_project_id
    iniset $TEMPEST_CONFIG identity tenant_id_1 $test_alt_project_id
    iniset $TEMPEST_CONFIG identity domain_id $test_domain_id
    iniset $TEMPEST_CONFIG identity default_domain_id $test_domain_id
    iniset $TEMPEST_CONFIG identity uri_v3 $OS_AUTH_URL
    iniset $TEMPEST_CONFIG identity v3_endpoint_type $DEFAULT_ENDPOINT_TYPE
    iniset $TEMPEST_CONFIG identity region $OS_REGION_NAME

    # Auth
    iniset $TEMPEST_CONFIG auth use_dynamic_credentials False
    iniset $TEMPEST_CONFIG auth test_accounts_file $TEMPEST_ACCOUNTS
    iniset $TEMPEST_CONFIG auth allow_tenant_isolation True

    #Set test user credentials
    export OS_USERNAME=$TEST_USERNAME
    export OS_PASSWORD=$TEST_PASSWORD
    export OS_PROJECT_DOMAIN_NAME=$TEST_DOMAIN_NAME
    export OS_USER_DOMAIN_NAME=$TEST_USER_DOMAIN_NAME
    export OS_PROJECT_NAME=$TEST_PROJECT_NAME
    export OS_TENANT_ID=$test_project_id

    # network
    while read -r NETWORK_TYPE NETWORK_UUID; do
        if [ "$NETWORK_TYPE" = "Internal" ]; then
            network_id="$NETWORK_UUID"
            network_id_alt="$NETWORK_UUID"
        fi
        networks+=($NETWORK_UUID)
    done < <($OPENSTACK_CMD network list --long -c ID -c "Router Type" | awk -F'|' '!/^(+--)|ID|aki|ari/ { print $3,$2 }')

    case "${#networks[*]}" in
        0)
            echo "Found no internal networks to use!"
            exit 1
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
    
    iniset $TEMPEST_CONFIG network internal_network_id $network_id
    iniset $TEMPEST_CONFIG network alt_internal_network_id $network_id_alt

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
}


if [ -d $OPENSTACK_CLI_VENV ]
then
   rm -rf $OPENSTACK_CLI_VENV
fi

echo "creating virtual env for openstack client"
virtualenv $OPENSTACK_CLI_VENV
. $OPENSTACK_CLI_VENV/bin/activate
pip install openstacksdk==0.9.1
pip install os-client-config==1.18.0
pip install python-openstackclient==2.6.0
configure_tempest
deactivate
echo "cleaning up openstack client virtual env"
rm -rf $OPENSTACK_CLI_VENV
