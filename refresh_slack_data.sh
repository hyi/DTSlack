#!/usr/bin/bash

# refresh_slack_data: pull data from slack API nightly and time stamp data for later message evolution analysis and visualization
# Author: Hong Yi

OUTPUT_DATA_PATH=/projects/xdci/slack_data
BACKUP_PATH=/projects/xdci/slack_data/backup
WEB_SLACK_PATH=/projects/xdci/www/translator/teamscience/slackviz

echo "*** backing up current working data for visualization ***"
cp ${WEB_SLACK_PATH}/*.json ${BACKUP_PATH}

echo "*** run python script to pull data using slack API ***"
SLACK_BOT_TOKEN=$2 python $1/slack_app.py $1 ${OUTPUT_DATA_PATH} inputData.json wordCloud.json rawMessage.txt
echo "*** slack data pull is complete ***"

echo "*** compare the new data with the old data to see whether time stamped data need to be created. Only time stamp data when it is different from the last pull"
[[ `diff ${BACKUP_PATH}/inputData.json ${OUTPUT_DATA_PATH}/inputData.json` ]] && (
    echo "*** time stamp the data for historical time evolution analysis later ***"
    cp ${OUTPUT_DATA_PATH}/inputData.json ${OUTPUT_DATA_PATH}/inputData-`date +"%m-%d-%y"`.json
    cp ${OUTPUT_DATA_PATH}/wordCloud.json ${OUTPUT_DATA_PATH}/wordCloud-`date +"%m-%d-%y"`.json
    cp ${OUTPUT_DATA_PATH}/rawMessage.txt ${OUTPUT_DATA_PATH}/rawMessage-`date +"%m-%d-%y"`.txt
    echo "*** copy updated data to web directory to refresh data ***"
    cp ${OUTPUT_DATA_PATH}/inputData.json ${WEB_SLACK_PATH}/inputData.json
    cp ${OUTPUT_DATA_PATH}/wordCloud.json ${WEB_SLACK_PATH}/wordCloud.json
    )

