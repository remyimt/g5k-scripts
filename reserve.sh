#!/bin/bash

function usage {
  echo "Reserve ressources. Options:
    -c, cluster names (e.g., 'graphene griffon')
    -d, date of the reservation
    -h, this help
    -l, display default values
    -n, number of nodes
    -o, hour of the reservation
    -t, duration of the experiment
"
exit 0
}

NB_NODES=3
# Duration of the experiment (hour)
EXPERIMENT_TIME=2
# The day YYYY-MM-DD
DATE=$(date +%F)
# The hour HH:MM:SS
#HOUR=$(date +%H:%M:%S -d "+1 hours")
HOUR=$(date +%H:%M:%S)
# Clusters
CLUSTER="none"

while getopts c:d:hln:o:t: name; do
	case $name in
    c)
      CLUSTER=$OPTARG
    ;;
		d)
      DATE=$OPTARG
		;;
		h)
		  usage
		;;
    l)
      echo "Default values of the reservation:
        Number of nodes: $NB_NODES
        Duration of the experiment $EXPERIMENT_TIME
        Reservation date: $DATE $HOUR
        Cluster requested: $CLUSTER"
      exit 0
    ;;
    n)
      NB_NODES=$OPTARG
    ;;
    o)
      HOUR=$OPTARG
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

if [ $CLUSTER == "none" ];then
  oarsub -l nodes=$NB_NODES,walltime=$EXPERIMENT_TIME -r "$DATE $HOUR" -t allow_classic_ssh -t deploy &> nodes.txt
else
  oarsub -p "cluster='$CLUSTER'" -l nodes=$NB_NODES,walltime=$EXPERIMENT_TIME -r "$DATE $HOUR" -t allow_classic_ssh -t deploy &> nodes.txt
fi

