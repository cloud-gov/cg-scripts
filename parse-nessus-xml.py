#!/usr/bin/env python3

"""
parse-nessus-xml.py

A script to parse Nessus scan files and generate various reports.

Improvements implemented:
- Replaced percentages with counts in the severity chart.
- Added a title stating that the chart is the MM Nessus Summary by Severity.
"""

import os
import sys
import logging
import argparse
import re
import traceback
import yaml
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt
import nessus_file_reader as nfr

# Configure logging
logger = logging.getLogger("NessusParser")


# Load list of Daemons from configuration
def get_script_directory():
    """Returns the directory where the current script is located."""
    return os.path.dirname(os.path.realpath(__file__))


def load_daemon_list():
    """Loads the daemon list from daemons.yaml located in the same directory as the script."""
    script_dir = get_script_directory()
    yaml_path = os.path.join(script_dir, "daemons.yaml")

    try:
        with open(yaml_path, "r") as file:
            data = yaml.safe_load(file)
            return data.get("daemons", [])
    except FileNotFoundError:
        logger.error(f"Daemon list file not found at {yaml_path}")
        return []
    except Exception as e:
        logger.error(f"Error loading daemon list: {e}")
        return []


DAEMONS = load_daemon_list()

# Load list of Log4J plugin IDs
LOG4J_PLUGINS = [155999, 156057, 156103, 156183, 156327, 156860, 182252]


def get_nessus_files(paths):
    """Retrieves Nessus files from provided file and directory paths."""
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
            logger.warning(f"Path '{path}' is not valid.")
    return nessus_files


def process_daemon_plugin(
    plugin_output, report_host_name, daemon_report, daemon_seen_count
):
    """Processes daemon plugins and tracks unknown daemons."""
    for line in plugin_output.splitlines():
        line = line.strip()
        if line and "The following running daemons are not managed by dpkg" not in line:
            daemon_seen_count += 1
            if not any(daemon in line for daemon in DAEMONS):
                daemon_report.setdefault(report_host_name, []).append(line)
    return daemon_seen_count


def process_log4j_vulnerability(report_item, log4j_report, report_host_name):
    """Processes Log4J vulnerabilities."""
    plugin_id = int(nfr.plugin.report_item_value(report_item, "pluginID"))

    # Filter out hosts that include 'diego-cell' or 'logsearch'
    if "diego-cell" in report_host_name or "logsearch" in report_host_name:
        return

    # Collect vulnerabilities of unknown origins
    log4j_report[plugin_id]["count"] += 1


def process_vulnerability(report_item, vuln_report, report_host_name):
    """Processes vulnerabilities for summary and work reports."""
    plugin_id = int(nfr.plugin.report_item_value(report_item, "pluginID"))
    plugin_name = nfr.plugin.report_item_value(report_item, "pluginName")
    severity = int(nfr.plugin.report_item_value(report_item, "severity"))
    cvss3_base_score = nfr.plugin.report_item_value(report_item, "cvss3_base_score")
    cvss3_risk_factor = nfr.plugin.report_item_value(report_item, "cvss3_risk_factor")

    # Filter out 'Info' level vulnerabilities (severity == 0)
    if severity == 0:
        return

    key = (severity, plugin_id)
    vuln_report.setdefault(
        key,
        {
            "plugin_name": plugin_name,
            "severity": severity,
            "cvss3_base_score": cvss3_base_score,
            "cvss3_risk_factor": cvss3_risk_factor,
            "hosts": set(),
        },
    )
    vuln_report[key]["hosts"].add(report_host_name)


def generate_daemon_report(
    daemon_report,
    daemon_seen_count,
    output_file=None,
    previous_report=None,
    output_format="text",
):
    """Generates a daemon report with comparison to the previous month."""
    report_content = []
    current_date = datetime.now().strftime("%Y-%m-%d")
    report_content.append(f"\n------- DAEMON REPORT ({current_date}) -------\n")
    report_content.append(f"Total daemons seen: {daemon_seen_count}")

    previous_daemons = {}
    if previous_report and os.path.exists(previous_report):
        with open(previous_report, "r") as f:
            for line in f:
                match = re.match(r"Host: (.+)", line)
                if match:
                    host = match.group(1)
                    daemons = []
                    for daemon_line in f:
                        daemon_line = daemon_line.strip()
                        if daemon_line.startswith("  "):
                            daemons.append(daemon_line.strip())
                        else:
                            break
                    previous_daemons[host] = daemons

    still_present = {}
    new_daemons = {}

    for host, daemons in daemon_report.items():
        if host in previous_daemons and set(daemons) == set(previous_daemons[host]):
            still_present[host] = daemons
        else:
            new_daemons[host] = daemons

    if not still_present:
        report_content.append("\nNo results carried over from previous month.")

    if still_present:
        report_content.append("\nStill present from last month (Not Fixed):")
        for host, daemons in still_present.items():
            report_content.append(f"\nHost: {host}")
            for daemon in daemons:
                report_content.append(f"  {daemon}")

    if new_daemons:
        report_content.append("\nNew daemons detected this month:")
        for host, daemons in new_daemons.items():
            report_content.append(f"\nHost: {host}")
            for daemon in daemons:
                report_content.append(f"  {daemon}")

    if not still_present and not new_daemons:
        report_content.append("\nNo unknown daemons found.")

    report_text = "\n".join(report_content)
    if output_file:
        if output_format == "html":
            html_content = "<html><body><pre>" + report_text + "</pre></body></html>"
            with open(output_file, "w") as f:
                f.write(html_content)
        elif output_format == "csv":
            # CSV output not applicable for this report
            pass
        else:
            with open(output_file, "w") as f:
                f.write(report_text)
    else:
        print(report_text)


def generate_log4j_report(log4j_report, output_file=None, previous_report=None):
    """Generates a Log4J report with counts of unknown origins."""
    report_content = []
    current_date = datetime.now().strftime("%Y-%m-%d")
    report_content.append(f"\n======= LOG4J REPORT ({current_date}) =======\n")

    # Initialize counts for all Log4J plugins
    for plugin_id in LOG4J_PLUGINS:
        log4j_report.setdefault(plugin_id, {"count": 0})

    for plugin_id in LOG4J_PLUGINS:
        count = log4j_report[plugin_id]["count"]
        report_content.append(f"\nLog4J plugin: {plugin_id}")
        report_content.append(
            f"\tLog4J violations of unknown origins found (UNSAFE): {count}"
        )

    report_text = "\n".join(report_content)
    if output_file:
        with open(output_file, "w") as f:
            f.write(report_text)
    else:
        print(report_text)


def generate_work_report(vuln_report, output_file=None):
    """Generates a work report containing all current vulnerabilities grouped by plugin ID."""
    report_content = []
    current_date = datetime.now().strftime("%Y-%m-%d")
    report_content.append(f"\n------- NESSUS WORK REPORT ({current_date}) -------\n")

    severity_mapping = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}

    for key in sorted(vuln_report.keys(), reverse=True):
        severity, plugin_id = key
        vuln = vuln_report[key]
        plugin_name = vuln["plugin_name"]
        affected_hosts = sorted(vuln["hosts"])
        host_count = len(affected_hosts)
        cvss_score = vuln["cvss3_base_score"] or "N/A"
        cvss_risk = vuln["cvss3_risk_factor"] or "N/A"

        report_content.append(
            f"\nPlugin ID: {plugin_id}, Severity: {severity_mapping.get(severity, 'Unknown')}, Plugin Name: {plugin_name}, CVSS: {cvss_score} ({cvss_risk})"
        )
        report_content.append(
            f"Affected Hosts ({host_count}): {', '.join(affected_hosts)}"
        )

    report_text = "\n".join(report_content)
    if output_file:
        with open(output_file, "w") as f:
            f.write(report_text)
    else:
        print(report_text)


def generate_summary_report(
    vuln_report, max_hosts, output_file=None, previous_report=None, output_format="text"
):
    """Generates a summary report with comparison to the previous month."""
    report_content = []
    current_date = datetime.now().strftime("%Y-%m-%d")
    report_content.append(f"\n------- SUMMARY REPORT ({current_date}) -------\n")

    # Load previous month's vulnerabilities if available
    previous_vulns = set()
    if previous_report and os.path.exists(previous_report):
        with open(previous_report, "r") as f:
            for line in f:
                match = re.match(r"Plugin ID: (\d+),", line)
                if match:
                    previous_vulns.add(int(match.group(1)))

    # Separate current vulnerabilities into categories
    still_present = []
    new_vulns = []

    for key in sorted(vuln_report.keys(), reverse=True):
        severity, plugin_id = key
        vuln = vuln_report[key]
        plugin_name = vuln["plugin_name"]
        affected_hosts = sorted(vuln["hosts"])
        host_count = len(affected_hosts)
        cvss_score = vuln["cvss3_base_score"] or "N/A"
        cvss_risk = vuln["cvss3_risk_factor"] or "N/A"

        vuln_entry = {
            "Plugin ID": plugin_id,
            "Severity": severity,
            "Plugin Name": plugin_name,
            "CVSS Score": cvss_score,
            "CVSS Risk": cvss_risk,
            "Hosts": affected_hosts,
            "Host Count": host_count,
        }
        if plugin_id in previous_vulns:
            still_present.append(vuln_entry)
        else:
            new_vulns.append(vuln_entry)

    # Aggregate data
    total_vulns = len(vuln_report)
    severity_counts = defaultdict(int)
    for key in vuln_report.keys():
        severity_counts[key[0]] += 1

    report_content.append(f"Total Vulnerabilities: {total_vulns}")
    report_content.append("Vulnerabilities by Severity:")
    severity_mapping = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}
    for severity_level in sorted(severity_counts.keys(), reverse=True):
        count = severity_counts[severity_level]
        report_content.append(
            f"  {severity_mapping.get(severity_level, 'Unknown')}: {count}"
        )

    # Generate severity pie chart
    generate_severity_pie_chart(severity_counts, output_file)

    if not still_present:
        report_content.append("\nNo results carried over from previous month.")

    # Include vulnerabilities still present from last month
    if still_present:
        report_content.append("\nStill present from last month (Not Fixed):")
        for vuln in still_present:
            report_content.append(
                f"\nPlugin ID: {vuln['Plugin ID']}, Severity: {severity_mapping.get(vuln['Severity'], 'Unknown')}, Plugin Name: {vuln['Plugin Name']}, CVSS: {vuln['CVSS Score']} ({vuln['CVSS Risk']})"
            )
            report_content.append(
                f"Affected Hosts ({vuln['Host Count']}): {', '.join(vuln['Hosts'][:max_hosts])}"
            )
            if vuln["Host Count"] > max_hosts:
                report_content.append("...")

    # Include new vulnerabilities this month
    if new_vulns:
        report_content.append("\nNew vulnerabilities this month:")
        for vuln in new_vulns:
            report_content.append(
                f"\nPlugin ID: {vuln['Plugin ID']}, Severity: {severity_mapping.get(vuln['Severity'], 'Unknown')}, Plugin Name: {vuln['Plugin Name']}, CVSS: {vuln['CVSS Score']} ({vuln['CVSS Risk']})"
            )
            report_content.append(
                f"Affected Hosts ({vuln['Host Count']}): {', '.join(vuln['Hosts'][:max_hosts])}"
            )
            if vuln["Host Count"] > max_hosts:
                report_content.append("...")

    report_text = "\n".join(report_content)
    if output_file:
        if output_format == "html":
            html_content = "<html><body><pre>" + report_text + "</pre></body></html>"
            with open(output_file, "w") as f:
                f.write(html_content)
        elif output_format == "csv":
            csv_file = output_file.replace(".txt", ".csv")
            with open(csv_file, "w") as f:
                f.write(
                    "Plugin ID,Severity,Plugin Name,CVSS Score,CVSS Risk,Host Count,Hosts\n"
                )
                for vuln in still_present + new_vulns:
                    f.write(
                        f"{vuln['Plugin ID']},{severity_mapping.get(vuln['Severity'], 'Unknown')},{vuln['Plugin Name']},{vuln['CVSS Score']},{vuln['CVSS Risk']},{vuln['Host Count']},\"{', '.join(vuln['Hosts'])}\"\n"
                    )
            logger.info(f"CSV summary report saved as {csv_file}")
        else:
            with open(output_file, "w") as f:
                f.write(report_text)
    else:
        print(report_text)


def generate_severity_pie_chart(severity_counts, output_file):
    """Generates a pie chart of vulnerabilities by severity with counts and a title."""
    labels = []
    sizes = []
    severity_mapping = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}
    for severity_level in sorted(severity_counts.keys(), reverse=True):
        severity_label = severity_mapping.get(severity_level, "Unknown")
        count = severity_counts[severity_level]
        labels.append(f"{severity_label} ({count})")
        sizes.append(count)

    if not sizes:
        logger.info("No vulnerabilities to display in pie chart.")
        return

    # Define autopct function to display counts
    def make_autopct(sizes):
        def my_autopct(pct):
            total = sum(sizes)
            count = int(round(pct * total / 100.0))
            return f"{count}"

        return my_autopct

    fig1, ax1 = plt.subplots()
    ax1.pie(sizes, labels=labels, autopct=None, startangle=140)
    ax1.axis("equal")

    # Add title with month number
    current_month_year = datetime.now().strftime("%Y-%m")
    ax1.set_title(f"{current_month_year} Nessus Summary by Severity")

    chart_file = output_file.replace(".txt", "_severity_chart.png")
    plt.savefig(chart_file)
    plt.close()
    logger.info(f"Severity pie chart saved as {chart_file}")


def validate_input_files(filenames):
    """Validates that the input files are accessible and readable."""
    valid_files = []
    for filename in filenames:
        if os.path.exists(filename) and os.path.isfile(filename):
            valid_files.append(filename)
        else:
            logger.warning(f"File not found or inaccessible: {filename}")
    return valid_files


def main():
    parser = argparse.ArgumentParser(description="Nessus XML Parser")
    parser.add_argument(
        "input_paths", nargs="+", help="Nessus scan files or directories"
    )
    parser.add_argument(
        "-l", "--log4j", action="store_true", help="Generate Log4J report"
    )
    parser.add_argument(
        "-d", "--daemons", action="store_true", help="Generate daemons report"
    )
    parser.add_argument(
        "-w", "--work", action="store_true", help="Generate Nessus Work report"
    )
    parser.add_argument(
        "-D", "--debug", action="store_true", help="Enable debug logging"
    )
    parser.add_argument(
        "-s", "--summary", action="store_true", help="Generate summary report"
    )
    parser.add_argument("-c", "--csv", action="store_true", help="Generate CSV output")
    parser.add_argument("-a", "--all", action="store_true", help="Generate all reports")
    parser.add_argument(
        "-m",
        "--max-hosts",
        type=int,
        default=6,
        help="Set maximum number of hosts to display (default: 6)",
    )
    parser.add_argument("-o", "--output", help="Specify output file for reports")
    parser.add_argument("--prev", help="Specify previous month's report for comparison")
    parser.add_argument(
        "--output-format",
        choices=["text", "html", "csv"],
        default="text",
        help="Specify output format",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="Nessus XML Parser 2.0",
        help="Show program's version number and exit",
    )

    args = parser.parse_args()

    # Set logging level
    numeric_level = getattr(logging, args.log_level.upper(), None)
    logging.basicConfig(
        level=numeric_level, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    if args.debug:
        logger.setLevel(logging.DEBUG)

    # Determine reports to generate
    report_log4j = report_daemons = report_summary = report_csv = report_work = False
    if args.all:
        report_log4j = report_daemons = report_summary = report_work = True
    else:
        report_log4j = args.log4j
        report_daemons = args.daemons
        report_summary = args.summary
        report_work = args.work
        report_csv = args.csv

    input_paths = args.input_paths
    filenames = get_nessus_files(input_paths)

    # User Input Validation
    filenames = validate_input_files(filenames)
    if not filenames:
        logger.error("No valid Nessus scan files found.")
        sys.exit(1)

    daemon_report = {}
    daemon_seen_count = 0
    vuln_report = {}
    log4j_report = defaultdict(lambda: {"count": 0})

    for filename in filenames:
        try:
            nessus_scan_file = filename
            root = nfr.file.nessus_scan_file_root_element(nessus_scan_file)
            file_name = nfr.file.nessus_scan_file_name_with_path(nessus_scan_file)
            logger.info(f"Processing file: {file_name}")

            for report_host in nfr.scan.report_hosts(root):
                report_host_name = nfr.host.report_host_name(report_host)

                for report_item in nfr.host.report_items(report_host):
                    plugin_id = int(
                        nfr.plugin.report_item_value(report_item, "pluginID")
                    )
                    plugin_output = nfr.plugin.report_item_value(
                        report_item, "plugin_output"
                    )

                    if report_log4j and plugin_id in LOG4J_PLUGINS:
                        process_log4j_vulnerability(
                            report_item, log4j_report, report_host_name
                        )

                    if report_daemons and plugin_id == 33851:
                        daemon_seen_count = process_daemon_plugin(
                            plugin_output,
                            report_host_name,
                            daemon_report,
                            daemon_seen_count,
                        )

                    if report_summary or report_work or report_csv:
                        process_vulnerability(
                            report_item, vuln_report, report_host_name
                        )

        except Exception as e:
            logger.error(f"Error processing file '{filename}': {e}")
            if args.debug:
                traceback.print_exc()

    if report_daemons:
        generate_daemon_report(
            daemon_report,
            daemon_seen_count,
            output_file=args.output,
            previous_report=args.prev,
            output_format=args.output_format,
        )

    if report_log4j:
        generate_log4j_report(
            log4j_report, output_file=args.output, previous_report=args.prev
        )

    if report_summary:
        generate_summary_report(
            vuln_report,
            args.max_hosts,
            output_file=args.output,
            previous_report=args.prev,
            output_format=args.output_format,
        )

    if report_work:
        generate_work_report(vuln_report, output_file=args.output)

    if report_csv and args.output:
        # Implement CSV output function as needed
        pass


if __name__ == "__main__":
    main()
