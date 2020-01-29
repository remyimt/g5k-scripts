# How to use these scripts
1. Reserve nodes: `./reserve.py`
2. Deploy the environment on the nodes: `./deploy.sh`
3. Delete the reservation: `./delete.sh -f`

# Access from any directories
* Edit/create ~/.bashrc
```
export PATH=$PATH:/home/$(whoami)/g5k-scripts
```

# Notes
* More options are available for every script: `./script.sh -h`
* Interactive jobs can be reserved with `./interactive.sh`
