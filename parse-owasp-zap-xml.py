#!/usr/bin/env python3

"""
parse-owasp-zap-xml.py

A script to parse OWASP ZAP XML report files and generate a summary report.
"""

import os
import logging
import argparse
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
import re

# Configure logging
logger = logging.getLogger("ZAPParser")


def parse_zap_report(filename):
    """Parse a ZAP XML report file and return vulnerabilities grouped by alert."""
    try:
        tree = ET.parse(filename)
        root = tree.getroot()
    except ET.ParseError as e:
        logger.error(f"Failed to parse XML in {filename}: {e}")
        return {}
    except FileNotFoundError:
        logger.error(f"File not found: {filename}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error parsing {filename}: {e}")
        return {}

    vulns = defaultdict(set)

    # ZAP reports use 'site' elements at the root
    for site in root.findall("site"):
        # 'alerts' may be a direct child of 'site'
        alerts_element = site.find("alerts")
        if alerts_element is None:
            continue  # No alerts in this site

        for alert in alerts_element.findall("alertitem"):
            plugin_id = alert.findtext("pluginid") or "Unknown"
            name = alert.findtext("alert") or "Unknown"
            riskcode = alert.findtext("riskcode") or "Unknown"
            riskdesc = alert.findtext("riskdesc") or ""
            instances_element = alert.find("instances")
            urls = set()
            if instances_element is not None:
                for instance in instances_element.findall("instance"):
                    uri = instance.findtext("uri")
                    if uri:
                        urls.add(uri)
            key = (plugin_id, name, riskcode, riskdesc)
            vulns[key].update(urls)
    return vulns


def generate_zap_summary(vulns, output_file=None, previous_report=None):
    """Generates a summary report of ZAP vulnerabilities, excluding 'Informational' level."""
    severity_mapping = {"0": "Informational", "1": "Low", "2": "Medium", "3": "High"}
    report_content = []
    current_date = datetime.now().strftime("%Y-%m-%d")
    report_content.append(f"\n------- ZAP SUMMARY REPORT ({current_date}) -------\n")

    previous_vulns = set()
    if previous_report and os.path.exists(previous_report):
        with open(previous_report, "r") as f:
            for line in f:
                match = re.match(r"Plugin ID: (\d+),", line)
                if match:
                    previous_vulns.add(match.group(1))

    still_present = []
    new_vulns = []

    # Process vulnerabilities
    for (plugin_id, name, riskcode, riskdesc), urls in vulns.items():
        # Exclude 'Informational' level vulnerabilities
        if riskcode == "0":
            continue
        severity = severity_mapping.get(riskcode, "Unknown")
        vuln_entry = {
            "Plugin ID": plugin_id,
            "Name": name,
            "Severity": severity,
            "Risk Description": riskdesc,
            "URLs": urls,
            "Count": len(urls),
        }
        if plugin_id in previous_vulns:
            still_present.append(vuln_entry)
        else:
            new_vulns.append(vuln_entry)

    # Include vulnerabilities still present from last month
    if still_present:
        report_content.append("\nStill present from last month (Not Fixed):")
        for vuln in still_present:
            report_content.append(
                f"\nPlugin ID: {vuln['Plugin ID']}, Severity: {vuln['Severity']}, Name: {vuln['Name']}, Count of URLs: {vuln['Count']}"
            )
    else:
        report_content.append("\nNo results carried over from previous month.")

    # Include new vulnerabilities this month
    if new_vulns:
        report_content.append("\nNew vulnerabilities this month:")
        for vuln in new_vulns:
            report_content.append(
                f"\nPlugin ID: {vuln['Plugin ID']}, Severity: {vuln['Severity']}, Name: {vuln['Name']}, Count of URLs: {vuln['Count']}"
            )
    else:
        report_content.append("\nNo new vulnerabilities found this month.")

    if not still_present and not new_vulns:
        report_content.append("\nNo vulnerabilities found.")

    report_text = "\n".join(report_content)
    if output_file:
        with open(output_file, "w") as f:
            f.write(report_text)
        logger.info(f"ZAP summary report saved to {output_file}")
    else:
        print(report_text)


def main():
    parser = argparse.ArgumentParser(description="OWASP ZAP XML Parser")
    parser.add_argument("input_files", nargs="+", help="ZAP XML report files")
    parser.add_argument(
        "-o", "--output", help="Specify output file for the summary report"
    )
    parser.add_argument(
        "--prev", help="Specify previous month's ZAP report for comparison"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level",
    )

    args = parser.parse_args()

    # Set logging level
    numeric_level = getattr(logging, args.log_level.upper(), None)
    logging.basicConfig(
        level=numeric_level, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Collect vulnerabilities from all input files
    all_vulns = defaultdict(set)
    for filename in args.input_files:
        logger.info(f"Processing file: {filename}")
        vulns = parse_zap_report(filename)
        for key, urls in vulns.items():
            all_vulns[key].update(urls)

    # Generate the summary report
    generate_zap_summary(all_vulns, output_file=args.output, previous_report=args.prev)


if __name__ == "__main__":
    main()
