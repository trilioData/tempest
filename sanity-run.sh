#!/bin/bash
BASE_DIR="$(pwd)"
PYTHON_CMD="python3"

TEST_LIST_FILE="$BASE_DIR/test-list"
TEST_RESULTS_FILE="$BASE_DIR/test_results"
SUITE_LIST=("tempest.api.workloadmgr.sanity")
REPORT_DIR="$BASE_DIR/Report"

#Clean old files
rm -f $TEST_LIST_FILE
rm -f $TEST_RESULTS_FILE
rm -rf logs

touch $TEST_RESULTS_FILE
mkdir -p $REPORT_DIR
rm -f results.html
sed -i '/test_results_file = /c test_results_file = "'$REPORT_DIR'/results.html"' tempest/reporting.py

touch $TEST_LIST_FILE
rm -rf ./lock
rm -rf /opt/lock
LOGS_DIR=`echo "$line" | sed  's/\./\//g'`
LOGS_DIR=logs/$LOGS_DIR
mkdir -p $LOGS_DIR
echo "running $line"
./run_tempest.sh -V tempest.api.workloadmgr.sanity.test_create_full_snapshot
if [ $? -ne 0 ]; then
   echo "$line FAIL"
fi
mv -f tempest.log $LOGS_DIR/

$PYTHON_CMD -c 'from tempest import reporting; reporting.add_sanity_results_to_tempest_report()'
$PYTHON_CMD -c 'from tempest import reporting; reporting.add_sanity_stats_to_tempest_report()'

