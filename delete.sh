#!/bin/bash

function usage {
  echo "Free ressources. Options:
    -f, delete all my current jobs
    -h, this help
    -j, Job ID
    -l, list my current jobs
    "
  exit 0
}

JOBS=""

while getopts fhj:l name; do
	case $name in
    f)
      JOBS=$(oarstat -u | sed 1d | sed 1d | awk '{print $1}')
    ;;
    h)
      usage
    ;;
    j)
      JOBS=$OPTARG
    ;;
    l)
      oarstat -u
      exit 0
    ;;
    ?)
      echo Option -$OPTARG not recognized!
      exit 13
    ;;
  esac
done

if [ -z "$JOBS" ]; then
  echo "ERROR: Job id is required!"
else
  for job in $JOBS; do
    oardel $job
  done
fi
