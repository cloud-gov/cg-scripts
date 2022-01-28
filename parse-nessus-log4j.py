#!/usr/bin/env python3

import nessus_file_reader as nfr
import os
import glob
import traceback
import time
import sys
import re
import pprint

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

l4j_plugin = 155999
path_dict = {}

vuln_report = {}
for report_host in nfr.scan.report_hosts(root):
    report_host_name = nfr.host.report_host_name(report_host)
    for report_item in nfr.host.report_items(report_host):
        plugin_id = int(nfr.plugin.report_item_value(report_item, 'pluginID'))
        plugin_output = nfr.plugin.report_item_value(report_item, 'plugin_output')

        if plugin_id == l4j_plugin:
            for line in plugin_output.splitlines():
                m = re.match(r'^  Path\s+: (\/.*)', line)
                if m:
                    path = m.group(1)
                    a = path_dict.get(path,list())
                    a.append(report_host_name)
                    path_dict[path] = a

pp = pprint.PrettyPrinter(indent=4)
for p in sorted(path_dict):
    print(p)
    pp.pprint(sorted(path_dict[p]))
