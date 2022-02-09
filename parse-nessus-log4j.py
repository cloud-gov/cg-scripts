#!/usr/bin/env python3

# This emits the paths, and hosts, for log4j findings
# For images with instance guids, like:
#   ['cf-production-diego-cell-24-cf-production']
#     /var/vcap/data/grootfs/store/unprivileged/images/395c7a88-7a1c-4001-55df-261d/diff/home/vcap/app/WEB-INF/lib/log4j-core-2.7.jar
# then SSH to diego-cell/24, run 'cfdot cell-state (cell_id)' and 
# use `jq` to find the process guid.  The first 36 chars are the app guid. 
#
# From there, use `cf curl` commands to find the app, space and org: 
#
#    name, 467435c6c6612e0b91cc843ae331523636a9d7e4a4214213c8500abaa4d3024b
#    in /var/vcap/data/grootfs/store/unprivileged/meta/dependencies.
#    There should be a file named with the container id instance_guid,
#    e.g. image:f34eb243-17e6-420d-73a7-2c39.json. Then you can use
#    cfdot cell-state to get from instance_guid to the process_guid,
#    and the first 36 chars of the process_guid is the app_id. from
#    https://community.pivotal.io/s/article/How-to-find-which-Apps-are-Running-in-a-Diego-Cell?language=en_US
#    with help from
#    https://github.com/cloudfoundry/garden-runc-release/blob/develop/docs/understanding_grootfs_store_disk_usage.md
#
# To run in a diego cell
# cat instance_guids | while read i; do
#  if ( echo $i | grep -q -- - ); then
#          jqcmd="jq '.LRPs[] | select (.instance_guid == \"$i\") | .process_guid'"
#          echo -n "\"$i\", "
#          cfdot cell-states | eval $jqcmd | cut -c1-36
#  else
#    echo "\"$i\", \"-\""
#  fi
# done
#    f=25f94c5b-fd5b-4508-44ed-5854
#    jjq="jq '.LRPs[] | select (.instance_guid == \"$f\")'"
#    cfdot cell-states | eval $jjq
# It seem that works for all cells from one query point.
# . The long Docker images can be ignored sinc ethey have the same App guid as the shorter names



import nessus_file_reader as nfr
import sys
import re
import pprint
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

import csv
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
