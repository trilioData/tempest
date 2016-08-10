#!/bin/bash -x

BASE_DIR="$(pwd)"
source test.properties

TEST_LIST_FILE="$BASE_DIR/test-list"
TEST_RESULTS_FILE="$BASE_DIR/test_results"
SUITE_NAME="tempest.api.workloadmgr.integration"

#Clean old files
rm -f $TEST_LIST_FILE
rm -f $TEST_RESULTS_FILE
rm -rf logs

tools/with_venv.sh ./run_tempest.sh --list-tests $SUITE_NAME > $TEST_LIST_FILE
sed -i '1,5d'  $TEST_LIST_FILE
sed -i 's/\[.*\]//' $TEST_LIST_FILE


while read -r line
do  
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

echo "Test results are written in $TEST_RESULTS_FILE"
$BASE_DIR/send_mail.py $TVAULT_VERSION
