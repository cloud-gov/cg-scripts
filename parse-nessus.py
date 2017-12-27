import xml.etree.ElementTree as etree
import sys

if len(sys.argv) == 1:
    print('please provide a path to a .nessus report')
    sys.exit(-1)
filename = sys.argv[1]

tree = etree.parse(filename)
root = tree.getroot()
vulnids = {}
for check in tree.findall('.//ReportItem'):
    pluginID = check.attrib['pluginID']
    id = 'audit-file {}, check-id {}, check-name {}, result {}'.format(
                                            check.find('cm:compliance-audit-file').text,
                                            check.find('cm:compliance-check-id').text,
                                            check.find('cm:compliance-check-name').text,
                                            check.find('cm:compliance-result').text
                                            )
    sites = vulnids.get(id, [])
    sites.append(sitename)
    vulnids[id] = sites

for key in vulnids:
    print(key)
    for site in vulnids[key]:
        print('\t{}'.format(site))
