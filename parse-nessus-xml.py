import nessus_file_reader as nfr
import os
import glob
import traceback
import time
import sys

import csv
csvwriter = csv.writer(sys.stdout)

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
print('')


vulnids = {}
vuln_report = {}
for report_host in nfr.scan.report_hosts(root):
    report_host_name = nfr.host.report_host_name(report_host)
    for report_item in nfr.host.report_items(report_host):
        plugin_id = int(nfr.plugin.report_item_value(report_item, 'pluginID'))
        risk_factor = nfr.plugin.report_item_value(report_item, 'risk_factor')
        plugin_name = nfr.plugin.report_item_value(report_item, 'pluginName')
        id = '{}, Risk: {}, Plugin Name: {}, https://www.tenable.com/plugins/nessus/{}'.format(
                                            plugin_id, risk_factor, plugin_name, plugin_id)
        this_vuln = {
            "id": plugin_id,
            "risk_factor": risk_factor,
            "plugin_name": plugin_name,
            "full_description": id
        }
        hosts = vulnids.get(id, [])
        hosts.append(report_host_name)
        vulnids[id] = hosts
        vuln_report[id] = this_vuln

print("------- SUMMARY ------\n")

for key in sorted(vulnids):
    if key.find("Risk: None") == -1 :
        affected_hosts = vulnids[key]
        print(key)
        if len(affected_hosts) > 4:
            print('\t{} affected hosts found ...'.format(len(affected_hosts)))
        else:
            for site in affected_hosts:
                print('\t{}'.format(site))


print("-------  CSV  ------\n")
remediation_plan="We use operating system 'stemcells' from the upstream BOSH open source project, and these libraries are part of those packages. They release updates frequently, usually every couple weeks or so, and we will deploy this update when they make it ready."
for vuln in sorted(vulnids):
    if vuln.find("Risk: None") == -1 :
        affected_hosts = vulnids[vuln]
        risk_factor = vuln_report[vuln]["risk_factor"] 
        if risk_factor == "Medium" :
            risk_factor = "Moderate"
        csvwriter.writerow(["CGXX","RA-5",vuln_report[vuln]["plugin_name"], "", "Nessus Scan Report", 
            vuln_report[vuln]["id"], str(len(affected_hosts)) + " production hosts", 
            "Eddie Tejeda", "None", remediation_plan, start_date.date(), "", "Resolve", "", mmddYY, "Yes", mmddYY,
            "CloudFoundry stemcell", risk_factor, risk_factor, "No", "No", "No" ])
