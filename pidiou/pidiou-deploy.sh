#!/bin/bash

SITE="nancy"
CLUSTER="graphene"
DURATION=6
ENVIRONMENT="jessie-x64-min"

echo "$(date) - Reserving resources on cluster '$CLUSTER' for $DURATION hours"

if [ -z "$CLUSTER" ]; then
  ../reserve.py -t $DURATION -n 1
else
  ../reserve.py -t $DURATION -n 1 -c $CLUSTER
fi

## Set the end to 10 minutes before the end of the job
end_seconds=$(( $(date -d "+$DURATION hours" +%s) - 600 ))
end_date=$(date -d "+$DURATION hours")

echo "$(date) - The experiment will end at $end_date"
echo "$(date) - Deploying the environement jessie-min"
../deploy.sh -e $ENVIRONMENT

NODE=$(cat /tmp/tools/node2deploy.txt | awk '{ print $1 }')
echo "$(date) - Using the node $NODE to deploy pidiou"
scp metrics-pdu.py pdu-generator.py install.sh root@$NODE:
ssh root@$NODE "./install.sh $SITE &> install.log &"
now_seconds=$(date +%s)
while [ $now_seconds -lt $end_seconds ]; do
  echo "$(date) - Waiting the end of the experiment at $end_date"
  sleep_time=3600
  now_seconds=$(date +%s)
  if [ $(( $end_seconds - $now_seconds )) -lt 3600 ]; then
    sleep_time=$(( $end_seconds - $now_seconds ))
  fi
  echo "$(date) - Sleeping $sleep_time seconds"
  sleep $sleep_time
done

echo "$(date) - Retrieving the monitoring data"
./monitoring-data.sh $NODE

