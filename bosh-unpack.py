#!/usr/bin/env python3

import sys
import urllib.request
import yaml

releases = {
        'aide' :            { 'repo' : '/cloud-gov/aide-boshrelease/master',
                                'vendor' : False },
        'awslogs-bionic' : { 'repo' : '/cloud-gov/cg-awslogs-boshrelease/master',
                                'vendor' : False },
        'clamav':            { 'repo' : '/cloud-gov/cg-clamav-boshrelease/master',
                                'vendor' : False },
        'fisma':            { 'repo' : '/cloud-gov/cg-harden-boshrelease/master', },
        'nessus-agent':      { 'repo' : '/cloud-gov/cg-nessus-agent-boshrelease/master', },
        'node-exporter':      { 'repo' : '/bosh-prometheus/node-exporter-boshrelease/master' },
        'secureproxy'  :    { 'repo' : '/cloud-gov/cg-secureproxy-boshrelease/master', },
        'shibboleth'  :    { 'repo' : '/cloud-gov/shibboleth-boshrelease/master', },
        'snort':            { 'repo' : '/cloud-gov/cg-snort-boshrelease/master', },
        'syslog'       :     { 'repo' : '/cloudfoundry/syslog-release/main' }
}

blobs="/config/blobs.yml"

for line in sys.stdin.readlines():
    print( line.strip() )
    rel=line.split('/')[0] or exit()
    url = "https://raw.githubusercontent.com" + releases[rel]['repo']+blobs
    #print( url )
    yaml_data = urllib.request.urlopen(url).read()
    data = yaml.safe_load(yaml_data)
    if data:
        print(list(data.keys()))
