#!/bin/bash

ENVIRONMENT="jessie-x64-base"
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

while getopts e:him: name; do
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

echo "Deploying '$ENVIRONMENT' to the current job"
if [ ! -e "$MACHINE_FILE" ]; then
  # Generate $MACHINE_FILE from job id
  if [ -z "$JOB_ID" ]; then
    JOB_ID=$(oarstat -u | grep $(whoami) | awk '{print $1}')
  fi
  echo "Use the job $JOB_ID"
  if [ $JOB_ID == "all" ]; then
    echo "Using all jobs for the deployment"
    for jobid in $(oarstat -u | grep $(whoami) | awk '{print $1}'); do
      oarstat -fj $JOB_ID | grep assigned_hostnames | awk '{print $ 3}' \
        | tr "+" "\n" | sed "s:^:    :" >> $MACHINE_FILE
    done
  else
    if [ $(echo $JOB_ID | wc -l) -ne 1 ]; then
      echo "More than one job is detected. Please select your job or use '-j all'"
    else
      oarstat -fj $JOB_ID | grep assigned_hostnames | awk '{print $ 3}'| tr "+" "\n" | sed "s:^:    :" > $MACHINE_FILE
    fi
  fi
fi
echo "Deploying '$ENVIRONMENT' to $(wc -l $MACHINE_FILE | awk '{ print $1 }') nodes"
kadeploy3 -f $MACHINE_FILE -e $ENVIRONMENT -k

