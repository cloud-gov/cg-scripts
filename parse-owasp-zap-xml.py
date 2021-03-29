#!/usr/bin/env python3

import xml.etree.ElementTree as etree
import sys

if len(sys.argv) == 1:
    print('please provide a path to an XML ZAP report')
    sys.exit(-1)
filename = sys.argv[1]

tree = etree.parse(filename)
root = tree.getroot()
vulnids = {}
for site in tree.findall('site'):
    sitename = site.attrib['name']
    if sitename.find('cloud.gov') != -1:
        for alert in site.findall('.//alertitem'):
            id = '{}, CWE id {}, WASC id {}, Risk {}, Plugin ID {}'.format(alert.find('name').text,
                                                    alert.find('cweid').text,
                                                    alert.findtext('wascid',"None"),
                                                    alert.find('riskdesc').text,
                                                    alert.find('pluginid').text)
            sites = vulnids.get(id, [])
            sites.append(sitename)
            vulnids[id] = sites
    else:
        print(f'Info - Skipping non-cloud.gov site: {sitename}', file=sys.stderr)

for key in sorted(vulnids):
    print(key)
    for site in sorted(vulnids[key]):
        print('\t{}'.format(site))
