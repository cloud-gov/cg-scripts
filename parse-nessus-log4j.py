#!/usr/bin/env python3

import nessus_file_reader as nfr
import os
import glob
import traceback
import time
import sys
import re

import csv
csvwriter = csv.writer(sys.stdout,quoting=csv.QUOTE_ALL)

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

l4j_cell = {}
l4j_logs = {}
l4j_misc = {}
l4j_stsh = {}
l4j_plugin = 155999
l4j_plugins = [ 155999, 156032, 156057, 156103, 156183 ]
path_dict = {}

vuln_report = {}
for report_host in nfr.scan.report_hosts(root):
    report_host_name = nfr.host.report_host_name(report_host)
#    print("===",report_host_name, nfr.host.number_of_compliance_plugins_per_result(report_host,"FAILED"),"===")
    for report_item in nfr.host.report_items(report_host):
#        if nfr.plugin.compliance_check_item_value(report_item, 'cm:compliance-result') != "PASSED":
#            print(nfr.plugin.compliance_check_item_value(report_item, 'cm:compliance-check-name'))
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
                    print("=== Log4j-core-2.11 plugin {}".format(path))

print("\n------- SUMMARY ------\n")

for k in sorted(vuln_report):
    if vuln_report[k]["risk_factor"] != "None":
        affected_hosts = vuln_report[k]["hosts"]
        affected_hosts.sort()
        print(vuln_report[k]["full_description"])
        if len(affected_hosts) > max_hosts:
            print('\t{} affected hosts found ...'.format(len(affected_hosts)))
        else:
            #for site in affected_hosts.sort():
            for site in affected_hosts:
                print('\t{}'.format(site))

