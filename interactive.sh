#!/bin/bash

function usage {
  echo "Reserve interactive ressources. Options:
    -h, this help
    -n, number of nodes
    -t, duration of the experiment (hour)
"
exit 0
}

NB_NODES=1
# Duration of the experiment (hour)
EXPERIMENT_TIME=6

while getopts hn:t: name; do
	case $name in
		h)
		  usage
		;;
    n)
      NB_NODES=$OPTARG
    ;;
    t)
      EXPERIMENT_TIME=$OPTARG
    ;;
    ?)
      echo Option -$OPTARG not recognized!
      exit 13
    ;;
	esac
done

echo "INFO: nb: $NB_NODES, time: $EXPERIMENT_TIME"
oarsub -l "nodes=$NB_NODES,walltime=$EXPERIMENT_TIME:00" -I
