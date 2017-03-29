#!/usr/bin/python

### snmpwalk -mALL -v1 -cpublic grimani-pdu-1.nancy.grid5000.fr iso.3.6.1.4.1.318.1.1.26.9.4.3.1.7 > toto

import datetime
from execo_g5k import get_resource_attributes, get_site_clusters
import json
import os
from pysnmp.hlapi import *
import subprocess
import sys 
import time
import traceback
import urllib2
import MySQLdb

# Variables
# Save the monitoring values to the database
database_backend = True
db_user = 'root'
db_password = 'strangehat'
db_name = 'pdu'
# Limit the number of PDU to query
pdu_filter = []
#pdu_filter = [ 'grimani-pdu-1', 'grimani-pdu-2' ]
# Set the pdu_filter from node names. Use short names in the node filter!
node_filter = []
#node_filter = [ 'grimani-1', 'graphene-2' ]
# Store the monitoring values to verify PDU behaviours
results = {}
# The site to monitor. You can only query PDU of your local site
site = "nancy"
# Waiting time in seconds between monitoring loops
sleep_time = 2
# Counters: statistics about PDU with right behaviour
total = 0
failed = 0

def compareEnd(oid, origin_oid):
    dot = oid.rfind('.')
    return oid[:dot].endswith(origin_oid[-5:])

def createPdu(uid):
    if uid in results:
        return False
    else:
        results[uid] = {}

def addValue(uid, value):
    outlet = len(results[uid]) + 1
    results[uid][outlet] = value
    if database_backend:
        cur = db.cursor()
        outlet_name = 'outlet-%d' % outlet
        if uid in outlet_map:
		if outlet_name in outlet_map[uid]:
		    cur.execute('INSERT INTO monitoring VALUES(%d, \'%s\', \'%s\', %d);' % (
			time.time(), uid, outlet_map[uid][outlet_name], value))
		elif outlet_map[uid]['per_outlets']:
		    cur.execute('INSERT INTO monitoring VALUES(%d, \'%s\', \'%s\', %d);' % (
			time.time(), uid, outlet, value))
		else:
		    cur.execute('INSERT INTO monitoring VALUES(%d, \'%s\', \'all\', %d);' % (
			time.time(), uid, value))
        elif pdu_description:
            print 'WARNING: No description for \'%s\'' % uid
            cur.execute('INSERT INTO monitoring VALUES(%d, \'%s-nodesc\', \'all\', %d);' % (
	        time.time(), uid, value))
        else:
            cur.execute('INSERT INTO monitoring VALUES(%d, \'%s-nodesc\', %d, %d);' % (
	        time.time(), uid, outlet, value))
            
        db.commit()
        cur.close()

def log(msg):
    print msg
    f = open(LOG_FILE, 'a')
    f.write('%s\n' % msg)
    f.close()

def ping(host):
    ping = subprocess.Popen(["ping", "-c", "1", host], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    out, error = ping.communicate()
    return len(error) == 0

# Use the first argument as site name followed by short node names to append to the node_filter
if len(sys.argv) > 1:
    site = sys.argv[1]
    for idx in range(2, len(sys.argv)):
        node_filter.append(sys.argv[idx])

# Set filenames
print 'Checking PDU for the site %s (filter=%s)' % (site, pdu_filter)
PDU_FILE = 'api-%s-pdus.json' % site
OUTLET_FILE = 'pdu-%s.json' % site
LOG_FILE = "snmp-%s-%s.log" % (datetime.datetime.now().strftime("%Y_%b_%d_%H_%M"), site)

# Configure MySQL
if database_backend:
    db = MySQLdb.connect(host='localhost', user=db_user, passwd=db_password, db=db_name)

# Use the OUTLET_FILE to associate monitoring values with nodes
pdu_description = os.path.isfile(OUTLET_FILE)

# Delete old log files
if os.path.isfile(LOG_FILE):
    os.remove(LOG_FILE)

# Browse the API to look for PDU
if os.path.isfile(PDU_FILE):
    print 'Using the file %s as data resource' % PDU_FILE
else:
    print 'Generating the file %s from the API' % PDU_FILE
    for l in  get_resource_attributes('/sites/%s/' % site)['links']:
        if 'pdus' in l.values():
            # Check there are PDU on the site
            pdus_exists = True
    if pdus_exists:
        data = get_resource_attributes('/sites/%s/pdus/' % site)
        f = open(PDU_FILE, 'w')
        f.write(json.dumps(data))
        f.close()
    else:
        print "No PDU on the site '%s'" % site
        sys.exit(13)

# Retrieve relationships between PDU and nodes
if pdu_description:
    outlet_map = json.load(open(OUTLET_FILE, 'r'))

# Set the pdu_filter from the node_filter (select the appropriate PDU)
if len(node_filter) > 0:
    if not pdu_description:
        print 'ERROR: The PDU description does not exist! Generate it with the script ./pdu-generator.py'
        sys.exit(13)
    pdu_map = {}
    error = False
    for node in node_filter:
        not_found = True
        for pdu in outlet_map:
            if not_found:
                for outlet in outlet_map[pdu]:
                    if outlet_map[pdu][outlet] == node:
                        not_found = False
                        pdu_filter.append(pdu)
                        if outlet_map[pdu]['per_outlets'] == False:
                            pdu_map[node] = {'outlet': 'N/A', 'pdu': pdu }
                            print """WARNING: PDU of the node \'%s\' does not measure the power consumption per
                            outlet!""" % node
                            print """WARNING: No accurate consumption for the node \'%s\', refer to the 
                            consumption of the PDU \'%s\'""" % (node, pdu)
                        else:
                            pdu_map[node] = {'outlet': outlet, 'pdu': pdu }
        if not_found:
            print 'ERROR: No pdu found for the node \'%s\'. Please remove it from the node_filter' % node
            error = True
    if error:
        print "ERROR: Some nodes in the node filter are missing in the PDU description. Aborting!"
        sys.exit()

# Retrieve the UID of PDU
while True:
    results = {}
    for pdu in json.load(open(PDU_FILE, 'r'))['items']:
        if pdu_description and pdu['uid'] not in outlet_map:
            print "==== %s ====" % pdu['uid']
            print 'WARNING: [%s] Ignore this PDU because it has no description' % pdu['uid']
        elif len(pdu_filter) == 0 or pdu['uid'] in pdu_filter:
            createPdu(pdu['uid'])
            total += 1
            print "==== %s ====" % pdu['uid']
            if ping(pdu['uid']):
                power = pdu['sensors'][0]['power']
                if 'snmp' in power:
                    if power['per_outlets']:
                        outlets = True
                        origin = power['snmp']['outlet_prefix_oid']
                    else:
                        outlets = False
                        origin = power['snmp']['total_oids'][0][0:-2]
                    print "oid (per_outlets): %s (%s)" % (origin, outlets)
                    try:
                        cmd = nextCmd(SnmpEngine(),
                            CommunityData('public', mpModel=0),
                            UdpTransportTarget((pdu['uid'], 161)),
                            ContextData(),
                            ObjectType(ObjectIdentity(origin))
                            )
                        must_continue = True
                        while must_continue:
                            data = next(cmd)[-1]
                            oid = str(data[0][0])
                            must_continue = compareEnd(oid, origin)
                            if must_continue:
                                addValue(pdu['uid'], int(data[0][1]))
                        # Detect errors in monitoring values
                        if outlets:
                            if len(results[pdu['uid']]) < 2:
                                failed += 1
                                log("[%s] Not enough values, %d values for PDU" % 
                                        (pdu['uid'], len(results[pdu['uid']])))
                        else:
                            # It is assumed that every PDU has at least 8 outlets
                            if len(results[pdu['uid']]) > 7:
                                failed += 1
                                log("[%s] Not enough values, %d values for PDU" % 
                                        (pdu['uid'], len(results[pdu['uid']])))
                    except Exception as e:
                        failed += 1
                        log("[%s] Fail to process monitoring values: %s" % (pdu['uid'], e))
                        traceback.print_exc(file=sys.stdout)
            else:
                failed += 1
                log("ERROR: [%s] Unreachable PDU" % pdu['uid'])
    # Wait before retrieving consumption again
    print 'Sleeping %d seconds' % sleep_time
    time.sleep(sleep_time)
    if not database_backend:
        for pdu in sorted(results):
            print '[%s]: %s' % (pdu, results[pdu])
log("test#: %d, failure#: %d, good#: %d" % (total, failed, total - failed))

