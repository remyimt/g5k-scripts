#!/usr/bin/python

import datetime
import getopt
import json
import os
import shutil
import subprocess
import sys
import urllib2

# Default values
display = False
nb_nodes = 1
nb_nodes_option = False
experiment_time = 2
reservation = None
clusters = []
nodes = []
queues = {}
queue_selection = False
# Directory to store temporary files
user = subprocess.check_output('whoami', shell=True)
TMP_DIR = '/home/%s/.g5k-scripts' % user[:-1]

def usage(return_code):
    print 'Reserve resources on grid5000. Options:'
    print '  -a: select the admin queue'
    print '  -c: select the clusters (eg., -c "grimani graphene")'
    print '  -d: set the reservation date (eg., 04-23-23h54 or 23-23h54 or 23h54)'
    print '  -h: this help'
    print '  -l: display the reservation settings (do not make the reservation)'
    print '  -m: set node names (eg., -m "grimani-1 grimani-6")'
    print '  -n: set the number of nodes'
    print '  -q: connect to the grid5000 API for the queue selection'
    print '  -t: set the duration of the experiment (hours)'
    sys.exit(return_code)

def select_queue(cluster_name):
    filename = '%s/%s.json' % (TMP_DIR, cluster_name)
    if not os.path.isfile(filename):
        url = "https://api.grid5000.fr/3.0/sites/%s/clusters/%s/nodes/%s-1.json?pretty" % (
                site, cluster_name, cluster_name)
        r = urllib2.urlopen(url)
        f = open('%s' % filename, 'w')
        f.write(r.read())
        f.close()
    data = json.load(open(filename, 'r'))['supported_job_types']['queues']
    data.remove('admin')
    return data[0]

# Get the site name and the cluster names
site = None
clusters_site = []
nodes_site = {}
p = subprocess.Popen('oarnodes -l', stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
p.stdout.flush()
for line in  p.stdout:
    # Remove empty lines
    if len(line) > 2:
        dotsplit = line.split('.')
        if site is None:
            site = dotsplit[1]
        cluster = line.split('-')[0]
        if cluster not in clusters_site:
            clusters_site.append(cluster)
        if line not in nodes_site:
            nodes_site[dotsplit[0]] = line.strip()

# Remove first argument (name of the script)
sys.argv = sys.argv[1:]

# Create temporary directory
if os.path.exists(TMP_DIR):
    shutil.rmtree(TMP_DIR)
os.mkdir(TMP_DIR)

# Parse arguments to modify default values
try:
    opts, args = getopt.getopt(sys.argv, "ac:d:hlm:n:qt:", ["noapi"])
except getopt.GetoptError:
    usage(13)
for opt, arg in opts:
    if opt == '-a':
        queues['admin'] = {'filter': [], 'clusters': [], 'nodes': []}
    elif opt == '-c':
        clusters = arg.split(' ')
    elif opt == '-d':
        try:
            d = datetime.datetime.now()
            if len(arg) == 5:
                # 23h54
                reservation = datetime.datetime.strptime('%d-%d-%d-%s:00' % (
                    d.year, d.month, d.day, arg), '%Y-%m-%d-%Hh%M:%S')
                if d.hour > reservation.hour:
                    # Schedule the reservation to the next month
                    reservation = datetime.datetime.strptime('%d-%d-%d-%s:00' % (
                        d.year, d.month, d.day + 1, arg), '%Y-%m-%d-%Hh%M:%S')
                    print "WARNING: Reservation for the next day: %s" % reservation
            elif len(arg) == 8:
                # 23-23h54
                reservation = datetime.datetime.strptime('%d-%d-%s:00' % (
                    d.year, d.month, arg),'%Y-%m-%d-%Hh%M:%S')
                # Schedule the reservation to the next month
                if d.day > reservation.day:
                    reservation = datetime.datetime.strptime('%d-%d-%s:00' % (
                        d.year, d.month + 1, arg),'%Y-%m-%d-%Hh%M:%S')
                    print "WARNING: Reservation for the next month: %s" % reservation
            elif len(arg) == 11:
                # 04-23-23h54
                reservation = datetime.datetime.strptime('%d-%s:00' % (
                    d.year, arg),'%Y-%m-%d-%Hh%M:%S')
                # Schedule the reservation to the next year
                if d.month > reservation.month:
                    reservation = datetime.datetime.strptime('%d-%s:00' % (
                        d.year + 1, arg),'%Y-%m-%d-%Hh%M:%S')
                    print "WARNING: Reservation for the next year: %s" % reservation
            else:
                print "Wrong date format!"
                usage(13)
        except:
            print "Wrong date format!"
            usage(13)
    elif opt == '-h':
        usage(0)
    elif opt == '-l':
        display = True
    elif opt == '-m':
        nodes = arg.split(' ')
    elif opt == '-n':
        nb_nodes_option = True
        nb_nodes = int(arg)
    elif opt == '-q':
         queue_selection = True
    elif opt == '-t':
        experiment_time = int(arg)

# Check incompatible options
if len(nodes) > 0 and len(clusters) > 0:
    print """ERROR: Incompatible options:
    can not specify node names (-m option) and cluster name (-c option) in the same command!"""
    sys.exit(13)

# Select clusters for the nodes
if len(nodes) > 0:
    for n in nodes:
        clustername = n[:n.index('-')]
        if clustername not in clusters:
            clusters.append(clustername)

# Check cluster names
for c in clusters:
    if c not in clusters_site:
        print 'ERROR: The cluster \'%s\' does not exist! Available clusters: %s' % (c, clusters_site)
        sys.exit(13)

# Check nodes names
for n in nodes:
    dot_idx = n.find('.')
    if dot_idx > 0:
        print 'ERROR: Please select nodes from short names! (use \'%s\' instead of \'%s\')' % (
                n[:dot_idx], n)
        sys.exit(13)
    if n not in nodes_site:
        print 'ERROR: The node \'%s\' does not exist!' % n
        sys.exit(13)

# Select the queues
for c in clusters:
    if queue_selection:
        # Select the appropriate queue from the grid5000 API
        myqueue = select_queue(c)
    else:
        if 'admin' in queues:
            myqueue = 'admin'
        else:
            # Add nodes to the default queue
            myqueue = 'default'
    if myqueue not in queues:
        queues[myqueue] = {'filter': [], 'clusters': [], 'nodes': []}
    queues[myqueue]['filter'].append(c)

# Remove clusters
if len(nodes) > 0:
    clusters = []

if len(nodes) == 0 and len(clusters) == 0:
    queues['default'] = {'filter': [], 'clusters': [], 'nodes': []}
    

# Check incompatible options
if nb_nodes_option and len(nodes) > 0 and nb_nodes > len(nodes):
    print 'ERROR: %d nodes in \'-n\' option and only %d nodes in \'-m\' option' % (nb_nodes, len(nodes))
    sys.exit(13)

if reservation is not None:
    if 'production' in queues:
        print """ERROR: Incompatible options:
        Can not use a reservation date with the production queue!
        Clusters in production queue: %s""" % queues['production']['filter']
        sys.exit(13)

# Process arguments for the oarsub command
queue_nb_nodes = int(nb_nodes / len(queues))
remain = nb_nodes - (queue_nb_nodes * len(queues))

for q in queues:
    if q == 'default':
        queue_arg = ''
    else:
        queue_arg = '-q %s' % q

    if remain == 0:
        queues[q]['nb_nodes'] = queue_nb_nodes
    else:
        remain -= 1
        queues[q]['nb_nodes'] = queue_nb_nodes + 1

    if len(clusters) == 0:
        cluster_arg = ''
    else:
        cluster_arg = '-p "cluster in ('
        for c in clusters:
            if c in queues[q]['filter']:
                queues[q]['clusters'].append(c)
                cluster_arg += '\'%s\', ' % c
        cluster_arg = cluster_arg[:-2] + ')"'

    # TODO: Select node names from pattern: graphene-[2-20]
    if len(nodes) == 0:
        nodenames_arg = ''
    else:
        nodenames_arg = '-p "network_address in ('
        for n in nodes:
            for f in queues[q]['filter']:
                if f in n:
                    queues[q]['nodes'].append(n)
                    nodenames_arg += '\'%s\', ' % nodes_site[n]
        nodenames_arg = nodenames_arg[:-2] + ')"'

    if not nb_nodes_option and len(nodes) > 0:
        nb_nodes = len(queues[q]['nodes'])
    if reservation is None:
        deploy_arg = '-t deploy \'sleep 10d\''
        reservation_arg = ''
    else:
        deploy_arg = "-t deploy"
        reservation_arg = '-r "%s"' % reservation.strftime('%F %H:%M:%S')

    if display:
        print 'Queue: %s' % q
        print '  Nb. of nodes: %d' % queues[q]['nb_nodes']
        if len(queues[q]['clusters']) > 0:
            print '  Clusters: %s' % queues[q]['clusters']
        if len(nodes) > 0:
            print '  Node names: %s' % queues[q]['nodes']
        print '  Duration of the experiment: %d hours' % experiment_time
        if reservation is None:
            print '  No reservation date'
        else:
            print '  Reservation Date: %s' % reservation
    else:
        # Execute the oarsub command
        cmd = 'oarsub %s %s -l nodes=%d,walltime=%d %s %s %s' % (
                queue_arg, cluster_arg, nb_nodes, experiment_time, nodenames_arg, reservation_arg, deploy_arg)
        p = subprocess.Popen(cmd, shell=True)
        p.wait()

