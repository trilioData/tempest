#!/bin/bash -x

BASE_DIR="$(pwd)"

TEST_LIST_FILE="$BASE_DIR/test-list"
TEST_RESULTS_FILE="$BASE_DIR/test_results"
SUITE_NAME="tempest.api.workloadmgr.integration"

#Clean old files
rm -f $TEST_LIST_FILE
rm -f $TEST_RESULTS_FILE

./run_tempest.sh --list-tests $SUITE_NAME > $TEST_LIST_FILE
sed -i '1,5d'  $TEST_LIST_FILE
sed -i 's/\[.*\]//' $TEST_LIST_FILE

filename="test-list"
while read -r line
do
    ./run_tempest.sh $line
	if [ $? -eq 0 ]; then
	   echo "$line PASSED" >> $TEST_RESULTS_FILE
    else
	   echo "$line FAILED" >> $TEST_RESULTS_FILE
	fi
done < "$filename"

echo "Test results are written in $TEST_RESULTS_FILE"
