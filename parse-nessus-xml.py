#!/usr/bin/env python3

import nessus_file_reader as nfr
import os
import glob
import traceback
import time
import sys

import csv
csvwriter = csv.writer(sys.stdout,quoting=csv.QUOTE_ALL)

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

print("\n------- SUMMARY ------\n")

for key in sorted(vuln_report):
    if vuln_report[key]["risk_factor"] != "None":
        affected_hosts = vuln_report[key]["hosts"]
        print(vuln_report[key]["full_description"])
#        print(vuln_report[key]["plugin_output"])
        if len(affected_hosts) > 6:
            print('\t{} affected hosts found ...'.format(len(affected_hosts)))
        else:
            for site in affected_hosts:
                print('\t{}'.format(site))

print("\n-------  CSV  ------\n")
remediation_plan="We use operating system 'stemcells' from the upstream BOSH open source project, and these libraries are part of those packages. They release updates frequently, usually every couple weeks or so, and we will deploy this update when they make it ready."
owner="Eddie Tejeda"
for vuln in sorted(vuln_report):
    if vuln_report[vuln]["risk_factor"] != "None":
        number_of_affected_hosts = len(vuln_report[vuln]["hosts"])
        risk_factor = vuln_report[vuln]["risk_factor"] 
        if risk_factor == "Medium" :
            risk_factor = "Moderate"
        csvwriter.writerow(["CGXX","RA-5",vuln_report[vuln]["plugin_name"], "", "Nessus Scan Report", 
            vuln_report[vuln]["id"], str(number_of_affected_hosts) + " production hosts", 
            owner, "None", remediation_plan, start_date.date(), "", "Resolve", "", mmddYY, "Yes", mmddYY,
            "CloudFoundry stemcell", risk_factor, risk_factor, "No", "No", "No" ])
