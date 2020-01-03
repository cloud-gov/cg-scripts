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
            id = '{}, CWE id {}, WASC id {}, Risk {}'.format(alert.find('name').text,
                                                    alert.find('cweid').text,
                                                    alert.find('wascid').text,
                                                    alert.find('riskdesc').text)
            sites = vulnids.get(id, [])
            sites.append(sitename)
            vulnids[id] = sites

for key in vulnids:
    print(key)
    for site in vulnids[key]:
        print('\t{}'.format(site))
