#!/usr/bin/python

from execo_g5k import get_resource_attributes, get_site_clusters
import json
import os
import sys

# Constants
DRIVER_SNMP = 'snmp'
DRIVER_WATTMETRE = 'wattmetre'
IGNORED_CLUSTERS = [ 'talc' ]

# Variables
pdus = {}
site = "nancy"

# Use the first argument as site name
if len(sys.argv) == 2:
    site = sys.argv[1]

INPUT_PDU = 'api-%s-pdus.json' % site
PDU_FILE = 'pdu-%s.json' % site
SWITCH_FILE = 'switch-%s.txt' % site
print "Generating the configuration file for the site '%s'" % site

# Classes
class Pdu:
    required = [ 'driver', 'name', 'site' ]
    outlet_nb = 99
    def __init__(self, site, pdu_name):
        self.properties = { 'name': pdu_name, 'site': site, 'outlets': {}}
    
    def __str__(self):
        if len(self.properties['outlets']) > 0:
            result = "%s(%s):\n" % (self.properties['name'], self.properties['per_outlets'])
            for o in sorted(self.properties['outlets']):
                result += "  %s: %s\n" % (o, self.properties['outlets'][o])
        else:
            result = "%s(%s)" % (self.properties['name'], self.properties['per_outlets'])
        return result

    def add_node(self, node_uid, outlet):
        if outlet == -1:
            outlet = self.outlet_gen()
        if outlet in self.properties['outlets']:
            print 'ERROR: Overriding values for PDU %s outlet %d: %s -> %s' % (self.properties['name'],
                    outlet, self.properties['outlets'][outlet], node_uid)
        self.properties['outlets'][outlet] = node_uid

    def check_description(self):
        ok = True
        for r in self.required:
            if r not in self.properties:
                ok = False
                print "Missing property '%s' for '%s'" % (r, self.properties['name'])
        return ok

    def get_name(self):
        return self.properties['name']

    def get_nodes(self):
        return self.properties['outlets']

    def is_empty(self):
        return len(self.properties['outlets']) == 0

    def is_per_outlet(self):
        return self.properties['per_outlets']

    def outlet_gen(self):
        self.outlet_nb += 1
        return self.outlet_nb

    def set_driver(self, driver_name, endpoint, per_outlets):
        """ Specify the driver for this pdu. endpoint should be an URL or a OID."""
        self.properties['per_outlets'] = per_outlets
        if driver_name == 'snmp':
            self.properties['driver'] = { 'type': 'snmp', 'community': 'public',
                    'protocol': 1, 'oid': endpoint }
        elif driver_name == 'wattmetre':
            self.properties['driver'] = { 'type': 'Json_url', 'url': endpoint }

class Switch:
    required = [ 'name', 'site' ]
    def __init__(self, site, switch_name):
        self.properties = { 'name': switch_name, 'site': site, 'linecards': {}}
    
    def __str__(self):
        if len(self.properties['linecards']) > 0:
            result = '%s:\n' % self.properties['name']
            linecards = self.properties['linecards']
            for l in sorted(linecards):
                result += '  %d:\n' % l
                for p in sorted(linecards[l]):
                    result += '    %d: %s\n' % (p, linecards[l][p])
        else:
            result = '%s' % self.properties['name']
        return result

    def add_node(self, node_uid, linecard, port):
        linecards = self.properties['linecards']
        if linecard not in linecards:
            linecards[linecard] = {}
        if port in linecards[linecard]:
            print 'ERROR: Overriding values for switch %s at %d/%d: %s -> %s' % (self.properties['name'],
                    linecard, port, linecards[linecard][port], node_uid)
        linecards[linecard][port] = node_uid

    def check_description(self):
        ok = True
        for r in self.required:
            if r not in self.properties:
                ok = False
                print "Missing property '%s' for '%s'" % (r, self.properties['name'])
        return ok

    def get_name(self):
        return self.properties['name']

    def is_empty(self):
        return len(self.properties['linecards']) == 0

    def set_pattern(self, pattern):
        self.properties['snmp_pattern'] = pattern

# Global functions
def map_power(nodes):
    for n in nodes:
        try:
            power = n['sensors']['power']
            if power['available']:
                if 'pdu' in power['via']:
                    for pdu in power['via']['pdu']:
                        if 'port' in pdu:
                            pdus[pdu['uid']].add_node(n['uid'], pdu['port'])
                        else:
                            pdus[pdu['uid']].add_node(n['uid'], -1)
        except Exception as e:
            print 'WARNING: Fail to retrieve power information about %s: %s' % (n['uid'], e)

# Get the list of PDU
# Checking the 'pdus' key is available
pdus_exists = False

if os.path.isfile(INPUT_PDU):
    print 'Using the file %s as data resource' % INPUT_PDU
else:
    print 'Generating the file %s from the API' % INPUT_PDU
    for l in  get_resource_attributes('/sites/%s/' % site)['links']:
        if 'pdus' in l.values():
            # Check there are PDU on the site
            pdus_exists = True
    if pdus_exists:
        data = get_resource_attributes('/sites/%s/pdus/' % site)
        f = open(INPUT_PDU, 'w')
        f.write(json.dumps(data))
        f.close()
    else:
        print "No PDU on the site '%s'" % site
        sys.exit(13)

for pdu in json.load(open(INPUT_PDU, 'r'))['items']:
    pdu_obj = Pdu(site, pdu['uid'])
    try:
        power = pdu['sensors'][0]['power']
        if 'snmp' in power:
            if power['per_outlets']:
                pdu_obj.set_driver(DRIVER_SNMP, power['snmp']['outlet_prefix_oid'], True)
            else:
                pdu_obj.set_driver(DRIVER_SNMP, power['snmp']['total_oids'][0][0:-2], False)
        if 'wattmetre' in power:
            pdu_obj.set_driver(DRIVER_WATTMETRE, power['wattmetre']['www']['url'], True)
        if pdu_obj.check_description():
            pdus[pdu_obj.get_name()] = pdu_obj
        else:
            print "ERROR: Wrong description for the PDU %s" % pdu_obj
    except Exception as e:
        print 'ERROR: Fail to retrieve power equipments on the site %s: %s' % (site, e)

if len(pdus) == 0:
    print 'ERROR: no detected PDU on the site %s' % site
else:
    # Map nodes to pdus
    print 'Associating nodes to PDU'
    for cluster in get_site_clusters(site, queues=None):
        print '== %s ==' % cluster
        if cluster in IGNORED_CLUSTERS:
            print 'INFO: Ignore the cluster: %s' % cluster
        else:
            map_power(get_resource_attributes('/sites/%s/clusters/%s/nodes' % (site, cluster))['items'])
    # Map switchs to pdus
    map_power(get_resource_attributes('/sites/%s/network_equipments' % site)['items'])
    # Warn about pdu without nodes
    for p in pdus.keys():
        if pdus[p].is_empty():
            print "INFO: Remove empty PDU: %s" % pdus[p]
            del pdus[p]

    # Dump the configuration to a file
    f = open(PDU_FILE, 'w')
    f.write('{\n')
    pdu_desc = ''
    for p in sorted(pdus):
        pdu_desc += '  "%s": {\n' % p
        pdu_desc += '    "per_outlets": %s,\n' % str(pdus[p].is_per_outlet()).lower()
        my_nodes = pdus[p].get_nodes()
        for outlet in my_nodes:
            pdu_desc += '    "outlet-%d": "%s",\n' % (outlet, my_nodes[outlet])
        pdu_desc = pdu_desc[:-2] + '\n'
        pdu_desc += '  },\n'
    pdu_desc = pdu_desc[:-2] + '\n'
    f.write('%s}\n' % pdu_desc)
    f.close()
    print "PDU configuration written in %s" % PDU_FILE

sys.exit()
# Get the list of switch
switchs = {}
for switch in get_resource_attributes('/sites/%s/network_equipments' % site)['items']:
    try:
        switch_obj = Switch(site, switch['uid'])
        l_counter=0
        for l in switch['linecards']:
            if 'snmp_pattern' not in l:
                if len(l) > 0:
                    print "ERROR: No snmp_pattern for %s/%s" % (switch_obj.get_name(), l_counter)
            else:
                snmp_pattern = l['snmp_pattern']
            if 'ports' in l:
                p_counter=0
                for p in l['ports']:
                    if 'uid' in p:
                        switch_obj.add_node(p['uid'], l_counter, p_counter)
                    p_counter += 1
            l_counter += 1
        if switch_obj.check_description():
            switchs[switch_obj.get_name()] = switch_obj
        else:
            print "ERROR: Wrong description for the switch %s" % switch_obj
    except Exception as e:
        print 'WARNING: Fail to retrieve network information about %s: %s' % (switch['uid'], e)

# Warn about switch without nodes
for s in switchs.keys():
    if switchs[s].is_empty():
        print "INFO: Remove empty switch: %s" % switchs[s]
        del switchs[s]

# Dump the configuration to a file
f = open(SWITCH_FILE, 'w')
for s in sorted(switchs):
    f.write('%s\n' % switchs[s])
f.close()
print "Switch configuration written in %s" % SWITCH_FILE

