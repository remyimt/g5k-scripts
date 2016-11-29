#!/bin/bash

function usage {
  echo "Reserve ressources. Options:
    -c, cluster names (-c 'graphene griffon')
    -d, date of the reservation
    -h, this help
    -l, display default values
    -m, reserve specific nodes from their name (-m 'econome-7 econome-20)
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
NODE_NAMES="none"
OARNODES_FILE="/tmp/remy/oarnodes-reserve.txt"
RESERVATION_FILE="/tmp/remy/oarsub-reserve.txt"

if [ ! -d /tmp/remy ]; then
  mkdir /tmp/remy
fi

rm -f $RESERVATION_FILE $OARNODES_FILE

while getopts c:d:hlm:n:o:t: name; do
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
    m)
      # "network_address in ('econome-22.nantes.grid5000.fr', 'econome-17.nantes.grid5000.fr')"
      grep_option=""
      oarnodes | grep 'network_address :' | sort | uniq | awk '$3!=""{print $3}' > $OARNODES_FILE
      NODE_NAMES="network_address in ("
      NB_NODES=0
      for node in $OPTARG; do
        NB_NODES=$(( $NB_NODES + 1 ))
        n=$(cat $OARNODES_FILE | grep "$node\.")
        error=""
        if [ -z "$n" ]; then
          error="$error $node"
        else
          NODE_NAMES="$NODE_NAMES'$n',"
        fi
      done
      if [ -z "$error" ]; then
        NODE_NAMES="${NODE_NAMES::-1})"
      else
        echo "Can not found the following nodes from oarnodes: $error"
        exit 0
      fi
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
  if [ "$NODE_NAMES" == "none" ]; then
    oarsub -l nodes=$NB_NODES,walltime=$EXPERIMENT_TIME -r "$DATE $HOUR" \
      -t allow_classic_ssh -t deploy &> $RESERVATION_FILE
  else
    oarsub -l nodes=$NB_NODES,walltime=$EXPERIMENT_TIME -p "$NODE_NAMES" -r "$DATE $HOUR" \
      -t allow_classic_ssh -t deploy &> $RESERVATION_FILE
  fi
else
  if [ "$NODE_NAMES" == "none" ]; then
    oarsub -p "cluster='$CLUSTER'" -l nodes=$NB_NODES,walltime=$EXPERIMENT_TIME -r "$DATE $HOUR" \
      -t allow_classic_ssh -t deploy &> $RESERVATION_FILE
  else
    echo "Incompatible options: can not specify node names (-m option) \
      and cluster name (-c option) in the same command"
  fi
fi

echo "Waiting for the job"
JOB_ID=$(cat $RESERVATION_FILE | grep OAR_JOB_ID | awk 'BEGIN {FS="="}; {print $2}')
while [ "$(oarstat -fj $JOB_ID | grep state |  awk 'BEGIN {FS="="}; {gsub(" ", "", $2); print $2}')" \
  != "Running" ]; do
  echo "Waiting for the job"
  sleep 20
done
echo "Your job is running with the ID $JOB_ID"

