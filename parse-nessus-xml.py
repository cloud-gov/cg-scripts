import nessus_file_reader as nfr
import os
import glob
import traceback
import time
import sys


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
for report_host in nfr.scan.report_hosts(root):
    report_host_name = nfr.host.report_host_name(report_host)
    for report_item in nfr.host.report_items(report_host):
        plugin_id = int(nfr.plugin.report_item_value(report_item, 'pluginID'))
        risk_factor = nfr.plugin.report_item_value(report_item, 'risk_factor')
        plugin_name = nfr.plugin.report_item_value(report_item, 'pluginName')
        id = '{}, Risk: {}, Plugin Name: {}, https://www.tenable.com/plugins/nessus/{}'.format(
                                            plugin_id, risk_factor, plugin_name, plugin_id)
        hosts = vulnids.get(id, [])
        hosts.append(report_host_name)
        vulnids[id] = hosts

for key in vulnids:
    if key.find("Risk: None") == -1 :
        affected_hosts = vulnids[key]
        print(key)
        if len(affected_hosts) > 4:
            print('\t{} affected hosts found ...'.format(len(affected_hosts)))
        else:
            for site in affected_hosts:
                print('\t{}'.format(site))
