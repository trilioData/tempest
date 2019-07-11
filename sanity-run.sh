#!/bin/bash -x
BASE_DIR="$(pwd)"
source /root/adminrc

TEST_LIST_FILE="$BASE_DIR/test-list"
TEST_RESULTS_FILE="$BASE_DIR/test_results"
SUITE_LIST=("tempest.api.workloadmgr.sanity")
REPORT_DIR="$BASE_DIR/Report"

#Clean old files
rm -f $TEST_LIST_FILE
rm -f $TEST_RESULTS_FILE
rm -rf logs

mkdir -p $REPORT_DIR
rm -f results.html
sed -i '/test_results_file=/c test_results_file="'$REPORT_DIR'/results.html"' tempest/reporting.py

testname=$(echo $SUITE_LIST| cut -d'.' -f 4)
touch $TEST_LIST_FILE
python -c "from tempest import reporting; reporting.get_tests(\"$TEST_LIST_FILE\",\""$BASE_DIR"/tempest/api/workloadmgr/"$testname"\")"
rm -rf /opt/lock
LOGS_DIR=`echo "$line" | sed  's/\./\//g'`
LOGS_DIR=logs/$LOGS_DIR
mkdir -p $LOGS_DIR
echo "running $line"
./run_tempest.sh -V tempest.api.workloadmgr.sanity.test_create_full_snapshot
if [ $? -ne 0 ]; then
   echo "$line FAILED"
fi
mv -f tempest.log $LOGS_DIR/

python -c 'from tempest import reporting; reporting.add_sanity_results_to_tempest_report()'

