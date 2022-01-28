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
owner="Lindsay Young"



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
        risk_factor = nfr.plugin.report_item_value(report_item, 'risk_factor')
        plugin_name = nfr.plugin.report_item_value(report_item, 'pluginName')
        plugin_output = nfr.plugin.report_item_value(report_item, 'plugin_output')
        description = f"{plugin_id}, Risk: {risk_factor}, Plugin Name: {plugin_name}, https://www.tenable.com/plugins/nessus/{plugin_id}"
        hosts = vuln_report.get(plugin_id, {}).get('hosts', [])
        hosts.append(report_host_name)
        this_vuln = {
            "id": plugin_id,
            "risk_factor": risk_factor,
            "plugin_name": plugin_name,
            "full_description": description,
            "plugin_output": plugin_output,
            "hosts": hosts
        }
        vuln_report[plugin_id] = this_vuln

        verbose=0
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
