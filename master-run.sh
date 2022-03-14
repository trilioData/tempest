#!/bin/bash
BASE_DIR="$(pwd)"
PYTHON_CMD="python3"

TEST_LIST_FILE="$BASE_DIR/test-list"
TEST_RESULTS_FILE="$BASE_DIR/test_results"
SUITE_LIST=("tempest.api.workloadmgr.sanity")
REPORT_DIR="$BASE_DIR/Report"

SUITE_D_CSV="suiteDuration.csv"
SUITE_D_HTML="suiteDuration.html"

#Clean old files
rm -f $TEST_LIST_FILE
rm -f $TEST_RESULTS_FILE
rm -rf logs

mkdir -p $REPORT_DIR
mkdir -p logs
sed -i '/test_results_file = /c test_results_file="'$REPORT_DIR'/results.html"' tempest/reporting.py
#PYTHON_CMD -c 'from tempest import reporting; reporting.consolidate_report_table()'

echo "SUITES,DURATION" >> ${SUITE_D_CSV}
for suite in "${SUITE_LIST[@]}"
do
    start=`date +%s`
    testname=$(echo $suite| cut -d'.' -f 4)
    $PYTHON_CMD -c "from tempest import reporting; reporting.setup_report('$testname')"
    touch $TEST_LIST_FILE
    $PYTHON_CMD -c "from tempest import reporting; reporting.get_tests(\"$TEST_LIST_FILE\",\""$BASE_DIR"/tempest/api/workloadmgr/"$testname"\")"
    ./run_tempest.sh -V tempest.api.workloadmgr.test_cleaner
    [ -s $TEST_LIST_FILE ]
    if [ $? -ne 0 ]
    then
        rm -rf $BASE_DIR/lock
        LOGS_DIR=`echo "$line" | sed  's/\./\//g'`
        LOGS_DIR=logs/$LOGS_DIR
        mkdir -p $LOGS_DIR
	mv tempest.log $LOGS_DIR/test_cleaner_tempest.log
        echo "running $suite"
        ./run_tempest.sh $suite
        if [ $? -ne 0 ]; then
            echo "$suite FAILED"
        fi
        mv -f tempest.log $LOGS_DIR/
    else
        while read -r line
        do  
            rm -rf $BASE_DIR/lock
            LOGS_DIR=`echo "$line" | sed  's/\./\//g'`
            LOGS_DIR=logs/$LOGS_DIR
            mkdir -p $LOGS_DIR
	    mv tempest.log $LOGS_DIR/test_cleaner_tempest.log
	    echo "running $line"
            ./run_tempest.sh $line
            if [ $? -ne 0 ]; then
 	         echo "$line FAILED" 
            fi
            mv -f tempest.log $LOGS_DIR/
    
        done < "$TEST_LIST_FILE"
        $PYTHON_CMD -c 'from tempest import reporting; reporting.end_report_table()'
    fi
    end=`date +%s`
    runtime=$( expr $end - $start)
    hours=$( printf "%02d\n" $(($runtime / 3600)))
    minutes=$( printf "%02d\n" $(( ($runtime % 3600) / 60 )))
    seconds=$( printf "%02d\n" $(( ($runtime % 3600) % 60 )))
    echo "$testname,$hours:$minutes:$seconds" >> ${SUITE_D_CSV}
done

echo "<br><br>" > ${SUITE_D_HTML}
echo "<table border=1 align=left>" >> ${SUITE_D_HTML}
header=true
while read INPUT;do if $header; then echo "<tr><th>${INPUT//,/</th><th>}</th></tr>";header=false; \
        else echo "<tr><td>${INPUT//,/</td><td>}</td></tr>";fi >> suiteDuration.html;done < suiteDuration.csv
echo "</table>" >> ${SUITE_D_HTML}

$PYTHON_CMD -c 'from tempest import reporting; reporting.consolidate_report()'

echo "Test results are written in $TEST_RESULTS_FILE"
sed -i -e '9s/passed_count = [0-9]*/passed_count = 0/' tempest/reporting.py
sed -i -e '10s/failed_count = [0-9]*/failed_count = 0/' tempest/reporting.py
