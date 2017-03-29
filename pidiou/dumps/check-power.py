#!/usr/bin/python

import datetime
import json
import MySQLdb
import os
import subprocess
import sys

db_user = 'remy'
db_password = 'remy'
nodes = []
#nodes = [ ['graphique-1'], ['graphique-2'], ['graphique-3'], ['graphique-4'], ['graphique-5'], ['graphique-6'],
#        ['graphite-1'], ['graphite-2'], ['grimani-1'], ['grimani-2'], ['grimani-3'] ]
LOG_FILE = 'check-power.log'

def log(msg):
    f = open(LOG_FILE, 'a')
    print msg
    f.write('%s\n' % msg)
    f.close()

def compareValue(a, b):
    if a > b:
        return a - b <= a * 0.1
    else:
        return b - a <= b * 0.1

if len(sys.argv) == 3:
    dump_file = sys.argv[1]
    site_name = sys.argv[2]
    db_name = dump_file.split('.')[0].replace('-', '_')
    LOG_FILE = '%s/%s.log' % (db_name, db_name)
    # Create the directory to store JSON files
    if not os.path.isdir(db_name):
        os.mkdir(db_name)
    # Remove existing log file
    if os.path.isfile(LOG_FILE):
        os.remove(LOG_FILE)
    # Create the database
    print "Compare %s to Kwapi %s" % (db_name, site_name)
    db = MySQLdb.connect(host='localhost', user=db_user, passwd=db_password)
    cur = db.cursor()
    cur.execute('SHOW DATABASES')
    db_found = False
    for row in cur.fetchall():
        if db_name in row:
            db_found = True
    if not db_found:
        print 'Creating the new database \'%s\'' % db_name
        cur.execute('CREATE DATABASE %s' % db_name)
        print 'Import monitoring values to the database'
        dump_import = subprocess.Popen('mysql -u%s -p%s %s < %s' % (db_user, db_password, db_name, dump_file), 
                stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)
        dump_import.wait()
    else:
        print 'Using the existing database \'%s\'' % db_name
    cur.close()
    db.close()
    # Retrieve the node names from the database
    db = MySQLdb.connect(host='localhost', user=db_user, passwd=db_password, db=db_name)
    cur = db.cursor()
    if len(nodes) == 0:
        print "Selecting the nodes from the database"
        cur.execute("SELECT DISTINCT outlet FROM monitoring WHERE LENGTH(outlet) > 3 ORDER BY outlet")
        nodes = cur.fetchall()
    for n in nodes:
        node_name = n[0]
        log('==== %s ====' % node_name)
        cur.execute('SELECT MIN(timestamp), MAX(timestamp) FROM monitoring WHERE outlet = \'%s\'' 
                % node_name)
        results = cur.fetchall()
        min_time = results[0][0]
        max_time = results[0][1]
        print 'Check power consumption from %s to %s' % (
                datetime.datetime.fromtimestamp(min_time), datetime.datetime.fromtimestamp(max_time))
        filename = '%s/%s-%d-%d.json' % (db_name, node_name, min_time, max_time)
        if not os.path.isfile(filename):
            print "Retrieving power values from Kwapi API"
            kwapi_url = '"http://kwapi.%s.grid5000.fr:12000/power/timeseries/?from=%d&to=%d&only=%s"' % (
                    site_name, min_time, max_time, node_name)
            ssh = subprocess.Popen([ "ssh", site_name, 'curl %s' % kwapi_url ], 
                    stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            out, error = ssh.communicate()
            f = open(filename, 'w')
            f.write(out)
            f.close()
        for node_data in json.load(open(filename, 'r'))['items']:
            cur.execute('SELECT timestamp, value FROM monitoring WHERE outlet = \'%s\'' % node_name)
            idx = 0
            kwapi_time = 0
            success = 0
            total = 0
            db_time = None
            for data in cur.fetchall():
                # Detect consumption peaks from database values
                '''
                if db_time is not None:
                    peak = data[1] * 100 / last_db_value
                    if  peak < 70:
                        print "peak in the database (%d, %d) and (%d, %d)" % (
                                db_time, last_db_value, data[0], data[1])
                    if  peak > 130:
                        print "peak in the database (%d, %d) and (%d, %d)" % (
                                db_time, last_db_value, data[0], data[1])
                '''
                db_time = data[0]
                while kwapi_time < db_time and idx < len(node_data['timestamps']) - 1:
                    idx += 1
                    kwapi_time = node_data['timestamps'][idx]
                    # Detect consumption peaks from Kwapi values
                    '''
                    peak = node_data['values'][idx] * 100 / node_data['values'][idx - 1]
                    if  peak < 70:
                        print "peak in the Kwapi (%d, %d) and (%d, %d)" % (
                                node_data['timestamps'][idx - 1], node_data['values'][idx - 1],
                                node_data['timestamps'][idx], node_data['values'][idx])
                    if  peak > 130:
                        print "peak in the Kwapi (%d, %d) and (%d, %d)" % (
                                node_data['timestamps'][idx - 1], node_data['values'][idx - 1],
                                node_data['timestamps'][idx], node_data['values'][idx])
                    '''
                if idx < len(node_data['timestamps']):
                    # Compare database values and Kwapi values
                    last_db_value = data[1]
                    if last_db_value > 20:
                        if abs(db_time - node_data['timestamps'][idx - 1]) < 5:
                            total += 1
                            if compareValue(last_db_value, node_data['values'][idx - 1]):
                                success += 1
                            else:
                                print 'ERROR: DB %d=%d, kwapi %d=%d' % (data[0], last_db_value,
                                        node_data['timestamps'][idx - 1], node_data['values'][idx - 1])

                        if abs(kwapi_time - db_time) < 5:
                            total += 1
                            if compareValue(last_db_value, node_data['values'][idx]):
                                success += 1
                            else:
                                print 'ERROR: DB %d=%d, kwapi %d=%d' % (data[0], last_db_value,
                                        node_data['timestamps'][idx], node_data['values'][idx])
            if total > 0:
                log('Success rate (values#): %d (%d)' % (success * 100 / total, total))
else:
    print 'Wrong argument! Usage: '
    print './check-power.py db-dump.db site_name'
