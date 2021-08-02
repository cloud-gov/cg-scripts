#!/usr/bin/env python3

import xml.etree.ElementTree as etree
import sys

if len(sys.argv) == 1:
    print('please provide paths to one more XML ZAP reports')
    sys.exit(-1)

filenames = sys.argv[1:]

vulnids = {}
for filename in filenames:
    tree = etree.parse(filename)
    root = tree.getroot()
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
