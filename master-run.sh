#!/bin/bash -x

BASE_DIR="$(pwd)"
source test.properties
source /root/engg-openrc-v2.sh

TEST_LIST_FILE="$BASE_DIR/test-list"
TEST_RESULTS_FILE="$BASE_DIR/test_results"
SUITE_LIST=("tempest.api.workloadmgr.integration" "tempest.api.workloadmgr.cli")
REPORT_DIR="$BASE_DIR/Report"

#Clean old files
rm -f $TEST_LIST_FILE
rm -f $TEST_RESULTS_FILE
rm -rf logs

mkdir -p $REPORT_DIR

for suite in "${SUITE_LIST[@]}"
do
    tools/with_venv.sh ./run_tempest.sh --list-tests $suite > $TEST_LIST_FILE
    sed -i '1,5d'  $TEST_LIST_FILE
    sed -i 's/\[.*\]//' $TEST_LIST_FILE

    echo $suite
    while read -r line
    do  
	echo $line
        rm -rf /opt/lock
        LOGS_DIR=`echo "$line" | sed  's/\./\//g'`
        LOGS_DIR=logs/$LOGS_DIR
        mkdir -p $LOGS_DIR
        ./run_tempest.sh $line
        if [ $? -eq 0 ]; then
	       echo "$line PASSED" >> $TEST_RESULTS_FILE
        else
 	       echo "$line FAILED" >> $TEST_RESULTS_FILE
        fi
        mv -f tempest.log $LOGS_DIR/
    
    
    done < "$TEST_LIST_FILE"
done

echo "Test results are written in $TEST_RESULTS_FILE"
$BASE_DIR/send_mail.py $TVAULT_VERSION $TO_ADDR
