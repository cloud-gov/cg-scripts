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

def remediation_plan(vuln):
    if ("JDK" in vuln) or ("Java" in vuln):
        return "cloud.gov services that depend on Java/JDK are patched via updates to code maintained by cloud.gov, for shibboleth or logsearch/ELK, or via vendor-provided updates from CloudFoundry, as noted in the Milestone Changes field"
    else:
        return "We use operating system 'stemcells' from the upstream BOSH open source project, and these libraries are part of those packages. They release updates frequently, usually every couple weeks or so, and we will deploy this update when they make it ready."

DAEMONS = """
    alertmanager
    auctioneer
    bbs
    binding-cache
    blackbox_exporter
    bosh_exporter
    bosh-dns
    bosh-dns-adapter
    bosh-dns-health
    broker
    cc.uploader
    cf_exporter
    concourse
    discovery-registrar
    domain-broker
    doomsday
    doppler
    elasticsearch_exporter
    file.server
    firehose_exporter
    forwarder-agent
    gnatsd
    gonats
    gorouter
    grafana
    guardian
    gdn
    locket
    log-cache
    log-cache-cf-auth-proxy
    log-cache-gateway
    log-cache-nozzle
    loggregator.agent
    loggregator_trafficcontroller
    metrics-agent
    metrics-discovery-registrar
    netmon
    nginx
    nginx_prometheus
    nginx/sbin/nginx
    node_exporter
    ntp
    oauth2.proxy
    opt
    policy-server
    policy-server-internal
    prom.scraper
    prometheus2
    pushgateway
    redis
    redis-server
    rep
    reverse_log_proxy
    reverse_log_proxy_gateway
    rlp
    rlp-gateway
    route.emitter
    secureproxy
    service-discovery-controller
    silk-controller
    silk-daemon
    ssh.proxy
    statsd.injector
    syslog-agent
    tps
    tps-watcher
    trafficcontroller
    udp-forwarder
    vxlan-policy-agent
""".split()

DAEMONS = '|'.join(DAEMONS)

daemon_count = 0
l4j_cell = {}
l4j_logs = {}
l4j_misc = {}
l4j_ghst = {}
l4j_plugins = [ 155999, 156032, 156057, 156103, 156183, 156327, 156860 ]

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

        # Match on known daemons:
        if plugin_id == 33851:
            for line in plugin_output.splitlines():
                if (len(line) < 1):
                    continue
                if "The following running daemons are not managed by dpkg" in line:
                    continue
                if re.search(rf'/var/vcap/bosh/bin/(bosh-agent|monit)', line):
                    daemon_count += 1
                    continue
                if re.search(rf'^/var/vcap/data/packages/({DAEMONS})/[0-9a-f]+/(s?bin/)?({DAEMONS})$', line):
                    daemon_count += 1
                    continue
                if re.search(rf'^/var/vcap/data/packages/(elasticsearch|idp|kibana|openjdk_1.8.0|openjdk-11|uaa)/[/[0-9a-z]+/bin/(java|node)$', line):
                    daemon_count += 1
                    continue
                if (re.search(rf'^/var/vcap/data/packages/ruby[-.r\d]+/[0-9a-z]+/bin/ruby$', line) and re.search(rf'cc-worker|admin-ui|bosh-0-cf-tooling', report_host_name)):
                    daemon_count += 1
                    continue
                print("== Unknown daemon found: ",report_host_name,": ", line)

        vuln_report[plugin_id] = this_vuln

##### LOG4J ####
        if plugin_id in l4j_plugins:
            for line in plugin_output.splitlines():
                if not (re.search(rf'^  Path', line)):
                    continue
                # nessus sometimes find customer files on phantom/ghost paths for the _container_ mount point
                if (re.search(rf'^  Path\s+: /usr/share/logstash/logstash-core/lib/jars/log4j.*jar$', line) or 
                    re.search(rf'^  Path\s+: /home/vcap/app/lib/boot/log4j-core-2.*jar$',line)):
                    l4j_ghst[plugin_id] = l4j_logs.get(plugin_id, 0) + 1 
                    print("== Phantom log4j plugin {} violation on {} found at path: {}".format(plugin_id, report_host_name, line))
                    continue
                # if host matches diego cell and path is in customer area:
                if (re.search(rf'^  Path\s+: /var/vcap/data/grootfs/store/unprivileged/(images|volumes)', line) and re.search(rf'-diego-cell-', report_host_name)):
                    l4j_cell[plugin_id] = l4j_cell.get(plugin_id, 0) + 1 
                    continue
                # if host matches logsearch and path is expected:
                if (re.search(rf'^  Path\s+: /var/vcap/data/packages/elasticsearch/[a-z0-9]+/lib/log4j-core-2.11.1.jar', line) and re.search(rf'^logsearch-', report_host_name)):
                    l4j_logs[plugin_id] = l4j_logs.get(plugin_id, 0) + 1 
                    continue
                print("== Unexpected log4j plugin {} violation on {} found at path: {}".format(plugin_id, report_host_name, line))
                l4j_misc[plugin_id] = l4j_misc.get(plugin_id, 0) + 1 

        

max_hosts = 6
for p in l4j_plugins:
    print("Log4j plugin: ", p)
    print("\tLog4J violations on Diego cells on phantom paths (safe): ", l4j_ghst.get(p, 0))
    print("\tLog4J violations on Diego cells in customer path (safe): ", l4j_cell.get(p, 0))
    print("\tLog4J violations on Logstash nodes at known path (safe): ", l4j_logs.get(p, 0))
    print("\tLog4J violations of unknown origins found (UNSAFE)     : ", l4j_misc.get(p, 0))
print("Known deamons seen: ", daemon_count)
print("\n------- SUMMARY ------\n")

for key in sorted(vuln_report):
    if vuln_report[key]["risk_factor"] != "None":
        affected_hosts = vuln_report[key]["hosts"]
        affected_hosts.sort()
        print(vuln_report[key]["full_description"])
#        print(vuln_report[key]["plugin_output"]) # For compliance?
        if len(affected_hosts) > max_hosts:
            print('\t{} affected hosts found ...'.format(len(affected_hosts)))
        else:
            #for site in affected_hosts.sort():
            for site in affected_hosts:
                print('\t{}'.format(site))

print("\n-------  CSV  ------\n")
for vuln in sorted(vuln_report):
    if vuln_report[vuln]["risk_factor"] != "None":
        number_of_affected_hosts = len(vuln_report[vuln]["hosts"])
        risk_factor = vuln_report[vuln]["risk_factor"] 
        if risk_factor == "Medium" :
            risk_factor = "Moderate"
        weakness_name=vuln_report[vuln]["plugin_name"]
        csvwriter.writerow(["CGXX","RA-5", weakness_name, "", "Nessus Scan Report", 
            vuln_report[vuln]["id"], str(number_of_affected_hosts) + " production hosts", 
            owner, "None", remediation_plan(weakness_name), start_date.date(), "", "Resolve", "", mmddYY, "Yes", mmddYY,
            "CloudFoundry stemcell", risk_factor, risk_factor, "No", "No", "No" ])
