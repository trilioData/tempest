#!/bin/bash -x
BASE_DIR="$(pwd)"
#source automation/openstack-build-scripts/build.properties
#source automation/openstack-build-scripts/openstack-auth.sh

TEST_LIST_FILE="$BASE_DIR/test-list"
TEST_RESULTS_FILE="$BASE_DIR/test_results"
SUITE_LIST=("tempest.api.workloadmgr.regression")
TEST_CASES_LIST=("tempest.api.workloadmgr.regression")
REPORT_DIR="$BASE_DIR/Report"

#Clean old files
rm -f $TEST_LIST_FILE
rm -f $TEST_RESULTS_FILE
rm -rf logs

mkdir -p $REPORT_DIR
sed -i '/test_results_file=/c test_results_file="'$REPORT_DIR'/results.html"' tempest/reporting.py
python -c 'from tempest import reporting; reporting.consolidate_report_table()'

for suite in "${SUITE_LIST[@]}"
do
    testname=$(echo $suite| cut -d'.' -f 4)
    python -c "from tempest import reporting; reporting.setup_report('$testname')"
    tools/with_venv.sh ./run_tempest.sh --list-tests $suite > $TEST_LIST_FILE
    sed -i '1,5d'  $TEST_LIST_FILE
    sed -i 's/\[.*\]//' $TEST_LIST_FILE

    while read -r line
    do  
        rm -rf /opt/lock
        LOGS_DIR=`echo "$line" | sed  's/\./\//g'`
        LOGS_DIR=logs/$LOGS_DIR
        mkdir -p $LOGS_DIR
	echo ""
        #./run_tempest.sh -V $line
        if [ $? -ne 0 ]; then
 	     echo "$line FAILED" 
        fi
        #mv -f tempest.log $LOGS_DIR/
    
    
    done < "$TEST_LIST_FILE"
    python -c 'from tempest import reporting; reporting.end_report_table()'
done

for test_case in "${TEST_CASES_LIST[@]}"
do
    python -c "from tempest import reporting; reporting.setup_report('$test_case')"
    while read -r line
    do
        rm -rf /opt/lock
        LOGS_DIR=`echo "$test_case" | sed  's/\./\//g'`
        LOGS_DIR=logs/$LOGS_DIR
        mkdir -p $LOGS_DIR
        #./run_tempest.sh -V $test_case
	if [ $? -ne 0 ]; then
             echo "$test_case FAILED"
        fi
        #mv -f tempest.log $LOGS_DIR/

    python -c 'from tempest import reporting; reporting.end_report_table()'
done

echo "Test results are written in $TEST_RESULTS_FILE"
sed -i -e '9s/passed_count = [0-9]*/passed_count = 0/' tempest/reporting.py
sed -i -e '10s/failed_count = [0-9]*/failed_count = 0/' tempest/reporting.py


