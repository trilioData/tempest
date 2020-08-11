#!/bin/bash -x
BASE_DIR="$(pwd)"

if [ -f $BASE_DIR/vms_file ]; then
   /bin/cp -f $BASE_DIR/vms_file $BASE_DIR/tempest/api/workloadmgr/
fi

if [ -f $BASE_DIR/volumes_file ]; then
   /bin/cp -f $BASE_DIR/volumes_file $BASE_DIR/tempest/api/workloadmgr/
fi

if [ -f $BASE_DIR/workloads_file ]; then
   /bin/cp -f $BASE_DIR/workloads_file $BASE_DIR/tempest/api/workloadmgr/
fi

rm -f tempest.log

function usage {
  echo "Usage: $0 [OPTION]..."
  echo "Run Tempest test suite"
  echo ""
  echo "  -V, --virtual-env        Always use virtualenv.  Install automatically if not present"
  echo "  -N, --no-virtual-env     Don't use virtualenv.  Run tests in local environment"
  echo "  -n, --no-site-packages   Isolate the virtualenv from the global Python environment"
  echo "  -f, --force              Force a clean re-build of the virtual environment. Useful when dependencies have been added."
  echo "  -u, --update             Update the virtual environment with any newer package versions"
  echo "  -s, --smoke              Only run smoke tests"
  echo "  -z, --functional         Only run functional tests"
  echo "  -t, --serial             Run testr serially"
  echo "  --list-tests <reg_exp>   List tests"
  echo "  -i, --list-failing       List failed cases from last testrun"
  echo "  -F, --run-failing        Run failed cases from last testrun"
  echo "  -C, --config             Config file location"
  echo "  -h, --help               Print this usage message"
  echo "  -d, --debug              Run tests with testtools instead of testr. This allows you to use PDB"
  echo "  -l, --logging            Enable logging"
  echo "  -L, --logging-config     Logging config file location.  Default is etc/logging.conf"
  echo "  -- [TESTROPTIONS]        After the first '--' you can pass arbitrary arguments to testr "
}

function list-failing-cases {
    ${wrapper} stestr failing
}

function list_tests() {
    ${wrapper} stestr list-tests $testrargs
}

function check_py_version() {
    py_str="python2"
    if ! hash python2; then
        echo "python2 is not installed"
        if ! hash python3; then
            echo "python3 is not installed"
            exit 1
        else
            echo "python3 is installed"
            py_str="python3"
        fi
    fi
    echo $py_str
}

testrargs=""
venv=${VENV:-.venv}
with_venv=tools/with_venv.sh
serial=0
always_venv=0
never_venv=0
no_site_packages=0
debug=0
force=0
wrapper=""
config_file=""
update=0
logging=0
logging_config=etc/logging.conf
test_filter_option=""
filepath_arg="$2"

if ! options=$(getopt -o VNnfuszthdFiC:lL: -l list-tests:virtual-env,no-virtual-env,no-site-packages,force,update,smoke,functional,serial,help,debug,list-tests,run-failing,list-failing,config:,logging,logging-config: -- "$@")
then
    # parse error
    usage
    exit 1
fi

if [ ! -z $PYTHON_VERSION ]
then
   py_str="python"$PYTHON_VERSION
   echo $py_str
else
   check_py_version
fi
eval set -- $options
first_uu=yes

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit;;
    -V|--virtual-env) always_venv=1; never_venv=0;;
    -N|--no-virtual-env) always_venv=0; never_venv=1;;
    -n|--no-site-packages) no_site_packages=1;;
    -f|--force) force=1;;
    -u|--update) update=1;;
    -d|--debug) debug=1;;
    -C|--config) config_file=$2; shift;;
    -s|--smoke) testrargs+="smoke"; tests_filter_option="smoke";;
    -z|--functional) testrargs+="functional"; tests_filter_option="functional";;
    -t|--serial) serial=1;;
    -l|--logging) logging=1;;
    -L|--logging-config) logging_config=$2; shift;;
    --list-tests) shift; shift; testrargs="$testrargs $1"; list_tests; exit;;
    -i|--list-failing) list-failing-cases; exit;;
    -F|--run-failing) testrargs="--failing"; $#=0;;
    --) [ "yes" == "$first_uu" ] || testrargs="$testrargs $1"; first_uu=no  ;;
    *) testrargs="$testrargs $1";;
  esac
  shift
done

if [ -n "$config_file" ]; then
    config_file=`readlink -f "$config_file"`
    export TEMPEST_CONFIG_DIR=`dirname "$config_file"`
    export TEMPEST_CONFIG=`basename "$config_file"`
fi

if [ $logging -eq 1 ]; then
    if [ ! -f "$logging_config" ]; then
        echo "No such logging config file: $logging_config"
        exit 1
    fi
    logging_config=`readlink -f "$logging_config"`
    export TEMPEST_LOG_CONFIG_DIR=`dirname "$logging_config"`
    export TEMPEST_LOG_CONFIG=`basename "$logging_config"`
fi

cd `dirname "$0"`

if [ $no_site_packages -eq 1 ]; then
  installvenvopts="--no-site-packages"
fi

function stestr_init {
  if [ ! -d .testrepository ]; then
      ${wrapper} stestr init
  fi
}

function run_tests {
  stestr_init
  ${wrapper} find . -type f -name "*.pyc" -delete
  export OS_TEST_TIMEOUT=172800
  export OS_TEST_PATH=./tempest/test_discover
  if [ $debug -eq 1 ]; then
      if [ "$testrargs" = "" ]; then
           testrargs="discover ./tempest/test_discover"
      fi
      ${wrapper} $py_str -m testtools.run $testrargs
      return $?
  fi
  echo $filepath_arg
  echo $py_str
  if [ -z "$filepath_arg" ]; then
      sed -i -e 's/self.tests_filter_option = "[a-z]*"/self.tests_filter_option = \"\"/g' .venv/lib/python*/site-packages/testrepository/testcommand.py
      if [ $serial -eq 1 ]; then
          ${wrapper} stestr run --subunit $testrargs | ${wrapper} subunit-2to1 | ${wrapper} tools/colorizer.py
      else
          ${wrapper} stestr run --subunit $testrargs | ${wrapper} subunit-2to1 | ${wrapper} tools/colorizer.py
      fi
  else
      sed -i -e 's/self.tests_filter_option = "[a-z]*"/self.tests_filter_option = \"'$tests_filter_option'\"/g' .venv/lib/python*/site-packages/testrepository/testcommand.py
      if [ $serial -eq 1 ]; then
          ${wrapper} stestr run --subunit "$filepath_arg" | ${wrapper} subunit-2to1 | ${wrapper} tools/colorizer.py
      else
          ${wrapper} stestr run --subunit "$filepath_arg" | ${wrapper} subunit-2to1 | ${wrapper} tools/colorizer.py
      fi
  fi
}

if [ $never_venv -eq 0 ]
then
  # Remove the virtual environment if --force used
  if [ $force -eq 1 ]; then
    echo "Cleaning virtualenv..."
    rm -rf ${venv}
  fi
  if [ $update -eq 1 ]; then
      echo "Updating virtualenv..."
      $py_str tools/install_venv.py $installvenvopts
  fi
  if [ -e ${venv} ]; then
    wrapper="${with_venv}"
  else
    if [ $always_venv -eq 1 ]; then
      # Automatically install the virtualenv
      $py_str tools/install_venv.py $installvenvopts
      wrapper="${with_venv}"
    else
      echo -e "No virtual environment found...create one? (Y/n) \c"
      read use_ve
      if [ "x$use_ve" = "xY" -o "x$use_ve" = "x" -o "x$use_ve" = "xy" ]; then
        # Install the virtualenv and run the test suite in it
        $py_str tools/install_venv.py $installvenvopts
        wrapper=${with_venv}
      fi
    fi
  fi
fi

run_tests
retval=$?

exit $retval

