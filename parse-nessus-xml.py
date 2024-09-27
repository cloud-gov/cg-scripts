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
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_script_directory():
    """
    Returns the directory where the current script is located.
    """
    return os.path.dirname(os.path.realpath(__file__))


def load_daemon_list():
    """
    Loads the daemon list from daemons.yaml located in the same directory as the script.
    """
    try:
        script_dir = get_script_directory()
        yaml_path = os.path.join(script_dir, "daemons.yaml")

        with open(yaml_path, "r") as file:
            data = yaml.safe_load(file)
            return data["daemons"]
    except FileNotFoundError:
        logger.error(f"Failed to locate daemons.yaml in {script_dir}")
        return []
    except Exception as e:
        logger.error(f"Error loading daemon list: {e}")
        return []


DAEMONS = load_daemon_list()

# List of Log4J-related plugin IDs
LOG4J_PLUGINS = [155999, 156057, 156103, 156183, 156327, 156860, 182252]

# Get today's date in YYYY-MM-DD format
current_date = date.today().strftime("%Y-%m-%d")


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
    """
    if ("JDK" in vuln) or ("Java" in vuln):
        return "cloud.gov services that depend on Java/JDK are patched via updates to code ..."
    else:
        return "We use operating system 'stemcells' from the upstream BOSH project that are updated every once to two weeks."


def get_nessus_files(paths):
    """
    Takes a list of file and directory paths and returns a list of Nessus scan files.
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


def process_daemon_plugin(
    plugin_output, report_host_name, daemon_report, daemon_seen_count
):
    """
    Processes the daemon plugin output to identify unknown daemons.
    Adds daemon counts and updates daemon report for unknown daemons.
    """
    for line in plugin_output.splitlines():
        line = line.strip()
        if not line or "The following running daemons are not managed by dpkg" in line:
            continue

        daemon_seen_count += 1
        if not any(daemon in line for daemon in DAEMONS):
            daemon_report.setdefault(report_host_name, []).append(line)

    return daemon_seen_count


def process_log4j_plugin(plugin_output, report_host_name, plugin_id, log4j_data):
    """
    Processes the Log4J plugin output to categorize findings.
    This function ensures that only plugins from the defined Log4J list are processed.
    """
    if plugin_id not in LOG4J_PLUGINS:
        return  # Skip non-Log4J plugins

    for line in plugin_output.splitlines():
        line = line.strip()
        if not re.search(r"^Path", line):
            continue

        # Patterns for known safe paths
        safe_patterns = [
            r"^Path\s+: /usr/share/logstash/logstash-core/lib/jars/log4j.*jar$",
            r"^Path\s+: /home/vcap/app/lib/boot/log4j-core-2.*jar$",
            r"^Path\s+: /var/vcap/data/grootfs/store/unprivileged/(images|volumes)",
            r"^Path\s+: /var/vcap/data/packages/elasticsearch/[a-z0-9]+/lib/log4j-core-2\.11\.1\.jar",
        ]
        if any(re.search(pattern, line) for pattern in safe_patterns):
            log4j_data["safe"][plugin_id] = log4j_data["safe"].get(plugin_id, 0) + 1
        else:
            log4j_data["unsafe"][plugin_id] = log4j_data["unsafe"].get(plugin_id, 0) + 1


def generate_log4j_report(log4j_data):
    """
    Generates the Log4J report based on the processed Log4J plugin data.
    Summarizes findings by plugin with counts of expected and unknown.
    """
    print(f"\n------- LOG4J REPORT ({current_date}) -------\n")

    if log4j_data["safe"]:
        print("\nExpected (Safe) Log4J Findings:")
        for plugin_id, count in log4j_data["safe"].items():
            print(f"Plugin ID {plugin_id}: {count} safe occurrences")

    if log4j_data["unsafe"]:
        print("\nUnknown (Unsafe) Log4J Findings:")
        for plugin_id, count in log4j_data["unsafe"].items():
            print(f"Plugin ID {plugin_id}: {count} unsafe occurrences")

    if not log4j_data["safe"] and not log4j_data["unsafe"]:
        print("No Log4J vulnerabilities found.")


def generate_log4j_conmon_summary(log4j_data):
    """
    Generates a summary for ConMon showing the unexpected Log4J occurrences.
    Outputs count per plugin, even if the count is 0.
    """
    print(f"\n------- LOG4J SUMMARY FOR CONMON ({current_date}) -------\n")

    for plugin_id in LOG4J_PLUGINS:
        count = log4j_data["unsafe"].get(plugin_id, 0)
        print(f"Plugin ID {plugin_id}: {count} unexpected occurrences")


def generate_daemon_report(daemon_report, daemon_seen_count):
    """
    Generates the daemon report, including a count of daemons seen.
    """
    print(f"\n------- Daemon REPORT ({current_date}) -------\n")
    print(f"Total daemons seen: {daemon_seen_count}")

    if daemon_report:
        for host, daemons in daemon_report.items():
            print(f"\nHost: {host}")
            for daemon in daemons:
                print(f"  {daemon}")
    else:
        print("No unknown daemons found.")


def generate_summary_report(vuln_report, max_hosts):
    """
    Generates the summary report.
    """
    print(f"\n------- SUMMARY ({current_date}) -------\n")
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
    """
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


def main():
    report_log4j = report_daemons = report_summary = report_csv = False
    max_hosts = 6
    opt_debug = False

    # Parse command-line arguments
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

    # Get the Nessus files
    input_paths = args
    filenames = get_nessus_files(input_paths)

    if not filenames:
        logger.error("No Nessus scan files found in the provided paths.")
        sys.exit(1)

    # Initialize dictionaries for reports
    vuln_report = {}
    daemon_report = {}
    log4j_data = {"safe": {}, "unsafe": {}}
    daemon_seen_count = 0

    # Process each Nessus scan file
    for filename in filenames:
        try:
            nessus_scan_file = filename
            root = nfr.file.nessus_scan_file_root_element(nessus_scan_file)
            file_name = nfr.file.nessus_scan_file_name_with_path(nessus_scan_file)
            logger.info(f"Processing file: {file_name}")

            # Process each host in the Nessus scan
            for report_host in nfr.scan.report_hosts(root):
                report_host_name = nfr.host.report_host_name(report_host)

                # Process each vulnerability item for the host
                for report_item in nfr.host.report_items(report_host):
                    plugin_id = int(
                        nfr.plugin.report_item_value(report_item, "pluginID")
                    )
                    plugin_output = nfr.plugin.report_item_value(
                        report_item, "plugin_output"
                    )

                    if report_log4j:
                        process_log4j_plugin(
                            plugin_output, report_host_name, plugin_id, log4j_data
                        )

                    if report_daemons and plugin_id == 33851:  # Daemon check plugin
                        daemon_seen_count = process_daemon_plugin(
                            plugin_output,
                            report_host_name,
                            daemon_report,
                            daemon_seen_count,
                        )

        except Exception as e:
            logger.error(f"Error processing file '{filename}': {e}")
            if opt_debug:
                traceback.print_exc()

    # Generate reports based on the selected options
    if report_log4j:
        generate_log4j_report(log4j_data)
        generate_log4j_conmon_summary(log4j_data)

    if report_daemons:
        generate_daemon_report(daemon_report, daemon_seen_count)

    if report_summary:
        generate_summary_report(vuln_report, max_hosts)

    if report_csv:
        with open(f"nessus_report_{date.today()}.csv", "w", newline="") as csvfile:
            csvwriter = csv.writer(csvfile)
            generate_csv_output(
                vuln_report,
                csvwriter,
                date.today(),
                "Your Name",
                date.today().strftime("%m/%d/%Y"),
            )


if __name__ == "__main__":
    main()
