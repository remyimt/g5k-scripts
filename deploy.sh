#!/bin/bash

# Jessie environment with g5k tools
ENVIRONMENT="jessie-x64-min"
MACHINE_FILE="/tmp/remy/node2deploy.txt"
JOB_ID=""

function usage {
  echo "Deploy environment to nodes. Options:
    -e, environment name (See 'kaenv3 -l')
    -h, this help
    -i, display information about jobs
    -j, job id to use for the deployment (use -j all to deploy on all jobs)
    -m, use machine names (-m 'econome-5 econome-10')
"
exit 0
}

rm -f $MACHINE_FILE

while getopts e:hij:m: name; do
	case $name in
    e)
      ENVIRONMENT=$OPTARG
    ;;
		h)
		  usage
		;;
    i)
      for jobid in $(oarstat -u | grep $(whoami) | awk '{print $1}'); do
        echo "---"
        echo "Job information"
        oarstat -fj $jobid \
          | grep 'job_array_id \| state \| startTime \| walltime' | grep -v "REDUCE_RESERVATION_WALLTIME"
        echo "Nodes"
        oarstat -fj $jobid | grep assigned_hostnames | awk '{print $ 3}'| tr "+" "\n" | sed "s:^:    :"
      done
      echo "---"
      exit 0
    ;;
    j)
      JOB_ID=$OPTARG
    ;;
    m)
      for machine in $OPTARG; do
        echo $machine >> $MACHINE_FILE
      done
    ;;
    ?)
      echo Option -$OPTARG not recognized!
      exit 13
    ;;
	esac
done

if [ ! -e $MACHINE_FILE ]; then
  if [ -z "$JOB_ID" ]; then
    echo "Retrieving the JOB_ID"
    nb_job=$(oarstat -u | grep $(whoami) | wc -l)
    if [ $nb_job -eq 1 ]; then
      JOB_ID=$(oarstat -u | grep $(whoami) | awk '{print $1}')
    else
      echo "ERROR: Wrong number of jobs (expected=1, found=$nb_job)"
      if [ $nb_job -gt 0 ]; then
        echo "Tips: You can deploy the environment on multiple jobs with the '-j all' option"
      fi
      exit 13
    fi
  fi

  if [ "$JOB_ID" == 'all' ]; then
    JOB_ID=""
    echo "Retrieving all job ID"
      for jobid in $(oarstat -u | grep $(whoami) | awk '{print $1}'); do
        JOB_ID="$JOB_ID $jobid"
      done
  fi

  if [ -z "$JOB_ID" ]; then
    echo "ERROR: Job id not found!"
    exit 13
  fi

  echo "Checking the state of every job"
  for jobid in $(echo $JOB_ID); do
    state=$(oarstat -fj $jobid | grep 'state' | awk '{ print $3 }')
    while [ $state != 'Running' ]; do
      state=$(oarstat -fj $jobid | grep 'state' | awk '{ print $3 }')
      echo "Wait for the job $jobid is running"
      sleep 30
    done
    echo "Job $jobid is running"
  done

  echo "Selecting the nodes"
  if [ ! -e "$MACHINE_FILE" ]; then
    # Generate $MACHINE_FILE from the job ID
    for jobid in $(echo $JOB_ID); do
      echo "Use the job $jobid"
      oarstat -fj $jobid | grep assigned_hostnames | awk '{print $ 3}' \
        | tr "+" "\n" | sed "s:^:    :" >> $MACHINE_FILE
    done
  fi
fi

echo "Deploying '$ENVIRONMENT' to $(wc -l $MACHINE_FILE | awk '{ print $1 }') nodes"
kadeploy3 -f $MACHINE_FILE -e $ENVIRONMENT -k

