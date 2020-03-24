#!/bin/bash -x
BASE_DIR="$(pwd)"

TEST_LIST_FILE="$BASE_DIR/test-list"
TEST_RESULTS_FILE="$BASE_DIR/test_results"
SUITE_LIST=("tempest.api.workloadmgr.sanity")
REPORT_DIR="$BASE_DIR/Report"

#Clean old files
rm -f $TEST_LIST_FILE
rm -f $TEST_RESULTS_FILE
rm -rf logs

mkdir -p $REPORT_DIR
sed -i '/test_results_file=/c test_results_file="'$REPORT_DIR'/results.html"' tempest/reporting.py
#python -c 'from tempest import reporting; reporting.consolidate_report_table()'

for suite in "${SUITE_LIST[@]}"
do
    testname=$(echo $suite| cut -d'.' -f 4)
    python -c "from tempest import reporting; reporting.setup_report('$testname')"
    touch $TEST_LIST_FILE
    python -c "from tempest import reporting; reporting.get_tests(\"$TEST_LIST_FILE\",\""$BASE_DIR"/tempest/api/workloadmgr/"$testname"\")"
    ./run_tempest.sh -V tempest.api.workloadmgr.test_cleaner
    while read -r line
    do  
        rm -rf $BASE_DIR/lock
        LOGS_DIR=`echo "$line" | sed  's/\./\//g'`
        LOGS_DIR=logs/$LOGS_DIR
        mkdir -p $LOGS_DIR
	echo "running $line"
        ./run_tempest.sh -V $line
        if [ $? -ne 0 ]; then
 	     echo "$line FAILED" 
        fi
        mv -f tempest.log $LOGS_DIR/
    
    done < "$TEST_LIST_FILE"
    python -c 'from tempest import reporting; reporting.end_report_table()'
done
python -c 'from tempest import reporting; reporting.consolidate_report()'

echo "Test results are written in $TEST_RESULTS_FILE"
sed -i -e '9s/passed_count = [0-9]*/passed_count = 0/' tempest/reporting.py
sed -i -e '10s/failed_count = [0-9]*/failed_count = 0/' tempest/reporting.py


