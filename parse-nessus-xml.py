#!/usr/bin/env python3

"""
parse-nessus-xml.py

A script to parse Nessus scan files and generate various reports.
"""

import sys
import os
import csv
import logging
import getopt
import re
import traceback
from datetime import date
import nessus_file_reader as nfr

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def print_help():
    print(
        "Usage: parse-nessus-xml.py [options] <nessus_scan_files_or_directories>\n"
        "\nOptions:\n"
        "-h, --help          Show this help message and exit\n"
        "-l, --log4j         Generate Log4J report\n"
        "-d, --daemons       Generate daemons report\n"
        "-D, --debug         Enable debug logging\n"
        "-s, --summary       Generate summary report\n"
        "-c, --csv           Generate CSV output\n"
        "-a, --all           Generate all reports\n"
        "-m, --max-hosts     Set maximum number of hosts to display (default: 6)"
    )
    sys.exit(1)


def remediation_plan(vuln):
    """
    Provides a remediation plan based on the vulnerability description.

    Args:
        vuln (str): The name or description of the vulnerability.

    Returns:
        str: A remediation plan.
    """
    if ("JDK" in vuln) or ("Java" in vuln):
        return (
            "cloud.gov services that depend on Java/JDK are patched via updates to code "
            "maintained by cloud.gov, for Shibboleth or Logsearch/ELK, or via vendor-provided "
            "updates from CloudFoundry, as noted in the Milestone Changes field."
        )
    else:
        return (
            "We use operating system 'stemcells' from the upstream BOSH open source project, "
            "and these libraries are part of those packages. They release updates frequently, "
            "usually every couple weeks or so, and we will deploy this update when they make it ready."
        )


def get_nessus_files(paths):
    """
    Takes a list of file and directory paths and returns a list of Nessus scan files.

    Args:
        paths (list): List of file and directory paths.

    Returns:
        list: List of Nessus scan file paths.
    """
    nessus_files = []
    for path in paths:
        if os.path.isfile(path):
            nessus_files.append(path)
        elif os.path.isdir(path):
            for root_dir, _, files in os.walk(path):
                for file in files:
                    if file.endswith(".nessus") or file.endswith(".xml"):
                        nessus_files.append(os.path.join(root_dir, file))
        else:
            logger.warning(f"Path '{path}' is not a valid file or directory.")
    return nessus_files


def main():
    # Initialize CSV writer
    csvwriter = csv.writer(sys.stdout, quoting=csv.QUOTE_ALL)

    # Check if any arguments are provided
    if len(sys.argv) == 1:
        print_help()

    # Get the command-line arguments, excluding the script name
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "hldDscam:",
            [
                "help",
                "log4j",
                "daemons",
                "debug",
                "summary",
                "csv",
                "all",
                "max-hosts=",
            ],
        )
    except getopt.GetoptError as e:
        logger.error(f"Argument parsing error: {e}")
        print_help()

    # Initialize report flags and settings
    report_log4j = report_daemons = report_summary = report_csv = False
    max_hosts = 6
    opt_debug = False

    # Process command-line options
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print_help()
        elif opt in ("-l", "--log4j"):
            report_log4j = True
        elif opt in ("-d", "--daemons"):
            report_daemons = True
        elif opt in ("-D", "--debug"):
            opt_debug = True
            logger.setLevel(logging.DEBUG)
        elif opt in ("-s", "--summary"):
            report_summary = True
        elif opt in ("-c", "--csv"):
            report_csv = True
        elif opt in ("-a", "--all"):
            report_log4j = report_daemons = report_summary = report_csv = True
        elif opt in ("-m", "--max-hosts"):
            try:
                max_hosts = int(arg)
            except ValueError:
                logger.error("Invalid value for --max-hosts. It must be an integer.")
                sys.exit(1)

    # The remaining arguments are the paths (files or directories)
    input_paths = args

    if not input_paths:
        logger.error(
            "No input paths provided. Please provide paths to Nessus XML reports or directories."
        )
        print_help()

    # Get list of Nessus scan files from input paths
    filenames = get_nessus_files(input_paths)

    if not filenames:
        logger.error("No Nessus scan files found in the provided paths.")
        sys.exit(1)

    # Initialize date variables
    today = date.today()
    mmddYY = today.strftime("%m/%d/%Y")
    owner = "Kelsey Foley"

    # Initialize counters and dictionaries
    l4j_cell = {}
    l4j_logs = {}
    l4j_misc = {}
    l4j_ghst = {}
    l4j_plugins = [155999, 156057, 156103, 156183, 156327, 156860, 182252]
    l4j_phantoms = []
    l4j_violations = []
    vuln_report = {}
    daemon_report = {}

    # Define known daemons
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
        eventgenerator
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
        log-cache-syslog-server
        loggregator.agent
        loggregator_trafficcontroller
        metrics-agent
        metrics-discovery-registrar
        metricsforwarder
        netmon
        nginx
        nginx_prometheus
        nginx/sbin/nginx
        node_exporter
        ntp
        oauth2.proxy
        operator
        policy-server
        policy-server-internal
        prom.scraper
        prometheus
        pushgateway
        redis
        redis-server
        rep
        reverse_log_proxy
        reverse_log_proxy_gateway
        rlp
        rlp-gateway
        route.emitter
        scalingengine
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
        uwsgi
        vxlan-policy-agent
    """.split()
    DAEMONS_PATTERN = "|".join(DAEMONS)

    # Process each Nessus scan file
    for filename in filenames:
        try:
            nessus_scan_file = filename
            root = nfr.file.nessus_scan_file_root_element(nessus_scan_file)
            file_name = nfr.file.nessus_scan_file_name_with_path(nessus_scan_file)
            file_size = nfr.file.nessus_scan_file_size_human(nessus_scan_file)
            start_date = nfr.scan.scan_time_start(root)
            logger.debug(f"Processing file: {file_name}")
            logger.debug(f"File size: {file_size}")
            logger.debug(f"Scan start date: {start_date}")

            # Process each host in the Nessus scan
            for report_host in nfr.scan.report_hosts(root):
                report_host_name = nfr.host.report_host_name(report_host)
                logger.debug(f"Processing host: {report_host_name}")
                # Process each vulnerability item for the host
                for report_item in nfr.host.report_items(report_host):
                    plugin_id = int(
                        nfr.plugin.report_item_value(report_item, "pluginID")
                    )
                    cvss3_base_score = nfr.plugin.report_item_value(
                        report_item, "cvss3_base_score"
                    )
                    plugin_name = nfr.plugin.report_item_value(
                        report_item, "pluginName"
                    )
                    plugin_output = nfr.plugin.report_item_value(
                        report_item, "plugin_output"
                    )

                    # Determine risk factor based on CVSS v3 base score
                    if cvss3_base_score is None:
                        cvss3_risk_factor = "None"
                    else:
                        try:
                            score = float(cvss3_base_score)
                            if score >= 9.0:
                                cvss3_risk_factor = "Critical"
                            elif score >= 7.0:
                                cvss3_risk_factor = "High"
                            elif score >= 4.0:
                                cvss3_risk_factor = "Medium"
                            elif score > 0.1:
                                cvss3_risk_factor = "Low"
                            else:
                                cvss3_risk_factor = "Undefined"
                        except ValueError:
                            cvss3_risk_factor = "Undefined"
                            logger.warning(
                                f"Invalid CVSS v3 base score: {cvss3_base_score}"
                            )

                    description = (
                        f"{plugin_id}, Risk: {cvss3_risk_factor}, Plugin Name: {plugin_name}, "
                        f"https://www.tenable.com/plugins/nessus/{plugin_id}"
                    )

                    # Update vulnerability report
                    vuln_info = vuln_report.get(
                        plugin_id,
                        {
                            "id": plugin_id,
                            "cvss3_base_score": cvss3_base_score,
                            "cvss3_risk_factor": cvss3_risk_factor,
                            "plugin_name": plugin_name,
                            "full_description": description,
                            "plugin_output": plugin_output,
                            "hosts": [],
                        },
                    )
                    vuln_info["hosts"].append(report_host_name)
                    vuln_report[plugin_id] = vuln_info

                    # Process specific plugins (e.g., daemons and Log4J)
                    if plugin_id == 33851:
                        process_daemon_plugin(
                            plugin_output,
                            report_host_name,
                            daemon_report,
                            DAEMONS_PATTERN,
                        )
                    if plugin_id in l4j_plugins:
                        process_log4j_plugin(
                            plugin_output,
                            report_host_name,
                            plugin_id,
                            l4j_cell,
                            l4j_logs,
                            l4j_misc,
                            l4j_ghst,
                            l4j_phantoms,
                            l4j_violations,
                            opt_debug,
                        )
        except Exception as e:
            logger.error(f"Error processing file '{filename}': {e}")
            if opt_debug:
                traceback.print_exc()

    # Generate reports based on options
    if report_log4j:
        generate_log4j_report(
            l4j_plugins,
            l4j_cell,
            l4j_logs,
            l4j_misc,
            l4j_ghst,
            l4j_phantoms,
            l4j_violations,
        )

    if report_daemons:
        generate_daemon_report(daemon_report)

    if report_summary:
        generate_summary_report(vuln_report, max_hosts)

    if report_csv:
        generate_csv_output(vuln_report, csvwriter, start_date, owner, mmddYY)


def process_daemon_plugin(
    plugin_output, report_host_name, daemon_report, DAEMONS_PATTERN
):
    """
    Processes the daemon plugin output to identify unknown daemons.

    Args:
        plugin_output (str): The output of the plugin.
        report_host_name (str): The name of the host.
        daemon_report (dict): The daemon report dictionary to update.
        DAEMONS_PATTERN (str): Regex pattern of known daemons.
    """
    for line in plugin_output.splitlines():
        line = line.strip()
        if not line or "The following running daemons are not managed by dpkg" in line:
            continue
        # Known daemon patterns
        known_patterns = [
            r"/var/vcap/store/nessus-manager/opt/nessus/sbin/nessusd",
            r"/var/vcap/bosh/bin/(bosh-agent|monit)",
            r"^/var/vcap/data/packages/("
            + DAEMONS_PATTERN
            + r")(2|-attic)?/[0-9a-f]+/(s?bin/)?("
            + DAEMONS_PATTERN
            + r")(-server|-asg-syncer)?$",
            r"^/var/vcap/data/packages/godojo/[0-9a-f]+/bin/bin/uwsgi$",
            r"^/var/vcap/data/packages/golangapiserver/[0-9a-f]+/api$",
            r"^/var/vcap/jobs/godojo/bin/uwsgi",
            r"^/var/vcap/data/packages/(elasticsearch|idp|kibana|kibana-platform|openjdk_1\.8\.0|openjdk[-_]11(\.0)?|openjdk[-_]17(\.0)?|uaa)/[0-9a-f]+/bin/(java|jre|node)$",
            r"^/var/vcap/data/packages/(nats|nats-v2-migrate|nats-server)/[0-9a-f]+/bin/(nats-wrapper|nats-server)$",
            r"^/var/vcap/data/packages/(director-)?ruby[-.\d]+/[0-9a-z]+/bin/ruby$",
        ]
        # Check if line matches any known pattern
        if any(re.search(pattern, line) for pattern in known_patterns):
            continue
        # Add unknown daemon to report
        daemon_report.setdefault(report_host_name, []).append(line)


def process_log4j_plugin(
    plugin_output,
    report_host_name,
    plugin_id,
    l4j_cell,
    l4j_logs,
    l4j_misc,
    l4j_ghst,
    l4j_phantoms,
    l4j_violations,
    opt_debug,
):
    """
    Processes the Log4J plugin output to categorize findings.

    Args:
        plugin_output (str): The output of the plugin.
        report_host_name (str): The name of the host.
        plugin_id (int): The plugin ID.
        l4j_cell, l4j_logs, l4j_misc, l4j_ghst (dict): Dictionaries to store counts.
        l4j_phantoms, l4j_violations (list): Lists to store messages.
        opt_debug (bool): Debug flag.
    """
    for line in plugin_output.splitlines():
        line = line.strip()
        if opt_debug:
            logger.debug(line)
        if not re.search(r"^Path", line):
            continue
        # Patterns for known safe paths
        safe_patterns = [
            r"^Path\s+: /usr/share/logstash/logstash-core/lib/jars/log4j.*jar$",
            r"^Path\s+: /home/vcap/app/lib/boot/log4j-core-2.*jar$",
        ]
        if any(re.search(pattern, line) for pattern in safe_patterns):
            l4j_ghst[plugin_id] = l4j_ghst.get(plugin_id, 0) + 1
            l4j_phantoms.append(
                f"Phantom Log4J plugin {plugin_id} violation on {report_host_name} found at path: {line}"
            )
            continue
        # Check for known safe paths on specific hosts
        if re.search(
            r"^Path\s+: /var/vcap/data/grootfs/store/unprivileged/(images|volumes)",
            line,
        ) and re.search(r"-diego-cell-", report_host_name):
            l4j_cell[plugin_id] = l4j_cell.get(plugin_id, 0) + 1
            continue
        if re.search(
            r"^Path\s+: /var/vcap/data/packages/elasticsearch/[a-z0-9]+/lib/log4j-core-2\.11\.1\.jar",
            line,
        ) and re.search(r"^logsearch-", report_host_name):
            l4j_logs[plugin_id] = l4j_logs.get(plugin_id, 0) + 1
            continue
        # Unknown violations
        l4j_violations.append(
            f"Unknown Log4J plugin {plugin_id} violation on {report_host_name} found at path: {line}"
        )
        l4j_misc[plugin_id] = l4j_misc.get(plugin_id, 0) + 1


def generate_log4j_report(
    l4j_plugins, l4j_cell, l4j_logs, l4j_misc, l4j_ghst, l4j_phantoms, l4j_violations
):
    """
    Generates the Log4J report.

    Args:
        l4j_plugins (list): List of Log4J plugin IDs.
        l4j_cell, l4j_logs, l4j_misc, l4j_ghst (dict): Dictionaries with counts.
        l4j_phantoms, l4j_violations (list): Lists of messages.
    """
    print("\n------- Log4J REPORT  ------\n")
    for pl in l4j_plugins:
        print(f"Log4J plugin: {pl}")
        print(
            f"\tLog4J violations on Diego cells on phantom paths (safe): {l4j_ghst.get(pl, 0)}"
        )
        print(
            f"\tLog4J violations on Diego cells in customer path (safe): {l4j_cell.get(pl, 0)}"
        )
        print(
            f"\tLog4J violations on Logstash nodes at known path (safe): {l4j_logs.get(pl, 0)}"
        )
        print(
            f"\tLog4J violations of unknown origins found (UNSAFE): {l4j_misc.get(pl, 0)}"
        )
    if l4j_phantoms:
        print("\nLog4J Phantoms:")
        for ph in l4j_phantoms:
            print(ph)
    if l4j_violations:
        print("\nLog4J Violations:")
        for vi in l4j_violations:
            print(vi)


def generate_daemon_report(daemon_report):
    """
    Generates the daemon report.

    Args:
        daemon_report (dict): Dictionary of unknown daemons.
    """
    print("\n------- Daemon REPORT  ------\n")
    total_unknown_daemons = sum(len(daemons) for daemons in daemon_report.values())
    print(f"Unknown daemons found on {len(daemon_report)} hosts:")
    for host, daemons in daemon_report.items():
        print(f"\nHost: {host}")
        for daemon in daemons:
            print(f"  {daemon}")
    if total_unknown_daemons == 0:
        print("No unknown daemons found.")


def generate_summary_report(vuln_report, max_hosts):
    """
    Generates the summary report.

    Args:
        vuln_report (dict): Dictionary of vulnerabilities.
        max_hosts (int): Maximum number of hosts to display per vulnerability.
    """
    print("\n------- SUMMARY ------\n")
    for key in sorted(vuln_report):
        vuln = vuln_report[key]
        if vuln["cvss3_base_score"] is not None:
            affected_hosts = sorted(set(vuln["hosts"]))
            print(vuln["full_description"])
            if len(affected_hosts) > max_hosts:
                print(f"\t{len(affected_hosts)} affected hosts found ...")
            else:
                for site in affected_hosts:
                    print(f"\t{site}")


def generate_csv_output(vuln_report, csvwriter, start_date, owner, mmddYY):
    """
    Generates CSV output for vulnerabilities.

    Args:
        vuln_report (dict): Dictionary of vulnerabilities.
        csvwriter (csv.writer): CSV writer object.
        start_date (datetime): Start date of the scan.
        owner (str): Owner of the vulnerabilities.
        mmddYY (str): Current date in MM/DD/YYYY format.
    """
    # CSV header
    csvwriter.writerow(
        [
            "POA&M ID",
            "Control Identifier",
            "Weakness/Deficiency Name",
            "Weakness/Deficiency Description",
            "Source Identifying Weakness",
            "Vulnerability ID",
            "Affected Components",
            "Point of Contact",
            "Status",
            "Required Corrective Actions",
            "Date Identified",
            "Scheduled Completion Date",
            "Type of Milestone",
            "Milestone Changes",
            "Completion Date",
            "Decommission/Removal",
            "Risk Acknowledgement Date",
            "System Component",
            "Initial Risk Rating",
            "Residual Risk Level",
            "Deviation Request",
            "RTM Required",
            "False Positive",
            "Deviation Rationale",
            "Supporting Documents",
            "Comments",
            "Auto Approval",
            "Known Exploited Vulnerability",
        ]
    )

    for key in sorted(vuln_report):
        vuln = vuln_report[key]
        if vuln["cvss3_base_score"] is not None:
            number_of_affected_hosts = len(set(vuln["hosts"]))
            cvss3_risk_factor = vuln["cvss3_risk_factor"]
            if cvss3_risk_factor == "Critical":
                cvss3_risk_factor = "High"  # Adjust for FedRAMP POA&M risk levels
            weakness_name = vuln["plugin_name"]
            # Prepare empty fields
            weakness_desc = sched_completion_date = milestone = deviation_rationale = (
                supporting_docs
            ) = comments = auto_approve = ""
            known_exploited = "No"
            csvwriter.writerow(
                [
                    "CGXX",  # POA&M ID placeholder
                    "RA-5",
                    weakness_name,
                    weakness_desc,
                    "Nessus Scan Report",
                    vuln["id"],
                    f"{number_of_affected_hosts} production hosts",
                    owner,
                    "Open",  # Status
                    remediation_plan(weakness_name),
                    start_date.date(),
                    sched_completion_date,
                    "Resolve",
                    milestone,
                    mmddYY,
                    "Yes",  # Decommission/Removal
                    mmddYY,  # Risk Acknowledgement Date
                    "CloudFoundry stemcell",
                    cvss3_risk_factor,
                    cvss3_risk_factor,
                    "No",  # Deviation Request
                    "No",  # RTM Required
                    "No",  # False Positive
                    deviation_rationale,
                    supporting_docs,
                    comments,
                    auto_approve,
                    known_exploited,
                ]
            )


if __name__ == "__main__":
    main()
