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
file_name = nfr.file.nessus_scan_file_name_with_path(nessus_scan_file)
file_size = nfr.file.nessus_scan_file_size_human(nessus_scan_file)
start_date = nfr.scan.scan_time_start(root)
print(f'File name: {file_name}')
print(f'File size: {file_size}')
print(f'Scan start date: {start_date}')

l4j_plugins = [ 155999, 156032, 156057, 156103, 156183 ]
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

import csv
csvwriter = csv.writer(sys.stdout,quoting=csv.QUOTE_ALL)
csvwriter.writerow(["Path", "Plugin Ids", "Node 0", "Instance GUID"])
for p in sorted(path_report):
    if re.match(r'/var/vcap/data/grootfs', p ):
        m = re.match(r'/var/vcap/data/grootfs/store/unprivileged/(images|volumes)/([^/]+)/', p)
        instance_guid = m.group(2)
        csvwriter.writerow(
            [   p, 
                sorted(path_report[p]["plugins"]),
                sorted(path_report[p]["hosts"])[0],
                instance_guid
            ])