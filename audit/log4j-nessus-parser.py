#!/usr/bin/env python3

# Usage:
#
#   ./$0 path-to-nessus.xml
# 
# This emits the paths, and hosts, for log4j findings, as CSV.  Getting 
# the final output of responsible users is a few more steps.
# 
# At that point I suggest you take the output, and paste it into a google sheet
# then copy all the instance guids, and be ready to paste them into a file
# called `instance_guids` on a deigo cell:
# 
# Then, on a diego cell, run the following to echo as more CSV the
# instance_guid and the app_guid.
# 
#   cat instance_guids | while read i; do
#    if ( echo $i | grep -q -- - ); then
#            jqcmd="jq '.LRPs[] | select (.instance_guid == \"$i\") | .process_guid'"
#            echo -n "\"$i\", "
#            cfdot cell-states | eval $jqcmd | cut -c1-36
#    else
#      echo "\"$i\", \"-\""
#    fi
#   done
#
# Now, paste all your app_guids, one per line, into another file, and set up
# to run the report with:
# 
#   pip3 install cloudfoundry-client
#   cf login --sso
#   cloudfoundry-client import_from_cf_cli`
#
# Finally:
#   ./log4j-report-users.py
#
# DO NOT email the list of vulns directly to customer. Determine what medium
# they want to use for vuln reports.
#
# - Peter Burkholder
# 



import nessus_file_reader as nfr
import sys
import re
import csv
from collections import defaultdict

from datetime import date
today = date.today()
mmddYY = today.strftime("%m/%d/%Y")

if len(sys.argv) == 1:
    print('please provide a path to an XML ZAP report')
    sys.exit(-1)
    
nessus_scan_file = sys.argv[1]

root = nfr.file.nessus_scan_file_root_element(nessus_scan_file)

l4j_plugins = [ 155999, 156032, 156057, 156103, 156183, 156860, 156327 ]
path_report = {}

for report_host in nfr.scan.report_hosts(root):
    report_host_name = nfr.host.report_host_name(report_host)
    for report_item in nfr.host.report_items(report_host):
        plugin_id = int(nfr.plugin.report_item_value(report_item, 'pluginID'))
        plugin_output = nfr.plugin.report_item_value(report_item, 'plugin_output')

        if plugin_id in l4j_plugins:
            for line in plugin_output.splitlines():
                m = re.match(r'^  Path\s+: (\/.*)', line)
                if m:
                    path = m.group(1)
                    path_info = path_report.get(path, defaultdict(list))
                    if plugin_id not in path_info["plugins"]:
                        path_info["plugins"].append(plugin_id)
                    if report_host_name not in path_info["hosts"]:
                        path_info["hosts"].append(report_host_name)
                    path_report[path] = path_info


# Path	Node 0	Instance GUID	Customer Path Name	Plugin Ids	App GUID	App Name	Space Name	Org Name	Org Manager	Space Developers																				


csvwriter = csv.writer(sys.stdout,quoting=csv.QUOTE_ALL)
csvwriter.writerow(["Path","Node_0","Instance_GUID","Customer_Path","Plugin_URLS","App_GUID","App_Name","Space_Name","Org_Name","Org_Managers","Space_Devs"])
for p in sorted(path_report):
    if re.match(r'/var/vcap/data/grootfs', p ):
        m = re.match(r'/var/vcap/data/grootfs/store/unprivileged/(images|volumes)/([^/]+)/(diff|root)?/?(fs)?(.*)$', p)
        instance_guid = m.group(2)
        customer_path = m.group(5)
        urls = ""
        for plugin_id in sorted(path_report[p]["plugins"]):
            urls += "https://www.tenable.com/plugins/nessus/{} ".format(plugin_id)
        
        csvwriter.writerow(
            [   p, 
                sorted(path_report[p]["hosts"])[0],
                instance_guid,
                f"/{customer_path}",
                urls,
            ])
