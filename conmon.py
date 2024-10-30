#!/usr/bin/env python3
# pip install matplotlib nessus-file-reader PyYAML

import os
import logging
import datetime
import argparse
import yaml
import subprocess
import shutil

# Configure logging
logger = logging.getLogger("ConMon")

# Default directories and settings
HOME_DIR = os.path.expanduser("~")
CMROOT = os.path.join(HOME_DIR, "Documents", "ConMon")
DAEMON_LIST_FILE = os.path.join(os.path.dirname(__file__), "daemons.yaml")


def load_daemon_list():
    try:
        with open(DAEMON_LIST_FILE, "r") as file:
            data = yaml.safe_load(file)
            return data["daemons"]
    except FileNotFoundError:
        logger.error(f"Daemon list YAML file not found at {DAEMON_LIST_FILE}")
        return []
    except Exception as e:
        logger.error(f"Error loading daemon list: {e}")
        return []


DAEMONS = load_daemon_list()


def setup_dirs(year, month):
    year_dir = os.path.join(CMROOT, str(year))
    month_dir = os.path.join(year_dir, str(month).zfill(2))
    reports_dir = os.path.join(year_dir, "reports")
    os.makedirs(month_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)
    logger.info(f"Month directory created or exists: {month_dir}")
    logger.info(f"Reports directory created or exists: {reports_dir}")
    return year_dir, month_dir, reports_dir


def flatten_directory(root_dir):
    for dirpath, _, filenames in os.walk(root_dir):
        if dirpath != root_dir:
            for filename in filenames:
                source_path = os.path.join(dirpath, filename)
                dest_path = os.path.join(root_dir, filename)
                if os.path.exists(dest_path):
                    logger.warning(
                        f"File already exists at destination, skipping move: {dest_path}"
                    )
                else:
                    shutil.move(source_path, dest_path)
                    logger.info(f"Moved {source_path} to {dest_path}")

    # Remove empty directories
    for dirpath, dirnames, _ in os.walk(root_dir, topdown=False):
        for dirname in dirnames:
            sub_dir = os.path.join(dirpath, dirname)
            try:
                os.rmdir(sub_dir)
                logger.info(f"Removed empty directory: {sub_dir}")
            except OSError as e:
                logger.warning(f"Could not remove directory {sub_dir}: {e}")


def collect_nessus_scans(scan_dir):
    flatten_directory(scan_dir)
    nessus_scans = []
    for root, _, files in os.walk(scan_dir):
        for file in files:
            if file.endswith(".nessus") or file.endswith(".xml"):
                nessus_scans.append(os.path.join(root, file))
    if not nessus_scans:
        logger.warning(
            f"No Nessus scan files found in the specified directory: {scan_dir}"
        )
    return nessus_scans


def get_last_month(year, month):
    if month == 1:
        return year - 1, 12
    else:
        return year, month - 1


def verify_file_exists(filepath):
    if os.path.exists(filepath):
        logger.info(f"Report successfully generated: {filepath}")
    else:
        logger.warning(f"Expected report file not found: {filepath}")


def run_report(report_type, nessus_scans, reports_dir, year, month, log_level):
    month_prefix = f"{str(month).zfill(2)}"
    last_year, last_month = get_last_month(year, month)
    last_month_prefix = f"{str(last_month).zfill(2)}"

    try:
        if report_type == "daemons":
            logger.info("Generating Daemon report...")
            output_file = os.path.join(reports_dir, f"{month_prefix}.daemons.txt")
            previous_report = os.path.join(
                reports_dir, f"{last_month_prefix}.daemons.txt"
            )
            subprocess.run(
                [
                    "python3",
                    "parse-nessus-xml.py",
                    "-d",
                    "-o",
                    output_file,
                    "--prev",
                    previous_report,
                    "--log-level",
                    log_level,
                ]
                + nessus_scans,
                check=True,
            )
            verify_file_exists(output_file)

        elif report_type == "log4j":
            logger.info("Generating Log4J report...")
            output_file = os.path.join(reports_dir, f"{month_prefix}.log4j.txt")
            previous_report = os.path.join(
                reports_dir, f"{last_month_prefix}.log4j.txt"
            )
            subprocess.run(
                [
                    "python3",
                    "parse-nessus-xml.py",
                    "-l",
                    "-o",
                    output_file,
                    "--prev",
                    previous_report,
                    "--log-level",
                    log_level,
                ]
                + nessus_scans,
                check=True,
            )
            verify_file_exists(output_file)

        elif report_type == "summary":
            logger.info("Generating Summary report...")
            summary_file = os.path.join(
                reports_dir, f"{month_prefix}.nessus_summary.txt"
            )
            previous_report = os.path.join(
                reports_dir, f"{last_month_prefix}.nessus_summary.txt"
            )
            subprocess.run(
                [
                    "python3",
                    "parse-nessus-xml.py",
                    "-s",
                    "-o",
                    summary_file,
                    "--prev",
                    previous_report,
                    "--log-level",
                    log_level,
                ]
                + nessus_scans,
                check=True,
            )
            verify_file_exists(summary_file)

        elif report_type == "work":
            logger.info("Generating Nessus Work report...")
            work_file = os.path.join(reports_dir, f"{month_prefix}.nessus_work.txt")
            subprocess.run(
                [
                    "python3",
                    "parse-nessus-xml.py",
                    "-w",
                    "-o",
                    work_file,
                    "--log-level",
                    log_level,
                ]
                + nessus_scans,
                check=True,
            )
            verify_file_exists(work_file)

        elif report_type == "zap":
            logger.info("Generating ZAP report...")
            zap_files = [
                file for file in nessus_scans if "ZAP" in os.path.basename(file)
            ]
            zap_summary = os.path.join(reports_dir, f"{month_prefix}.zap_summary.txt")
            last_zap_summary_path = os.path.join(
                reports_dir, f"{last_month_prefix}.zap_summary.txt"
            )
            if zap_files:
                try:
                    subprocess.run(
                        [
                            "python3",
                            "parse-owasp-zap-xml.py",
                            "-o",
                            zap_summary,
                            "--prev",
                            last_zap_summary_path,
                            "--log-level",
                            log_level,
                        ]
                        + zap_files,
                        check=True,
                    )
                    verify_file_exists(zap_summary)
                except subprocess.CalledProcessError as e:
                    logger.error(f"Error processing ZAP files: {e}")
            else:
                logger.warning("No ZAP files found for report generation.")

        elif report_type == "all":
            logger.info("Generating all reports...")
            run_report("daemons", nessus_scans, reports_dir, year, month, log_level)
            run_report("log4j", nessus_scans, reports_dir, year, month, log_level)
            run_report("summary", nessus_scans, reports_dir, year, month, log_level)
            run_report("work", nessus_scans, reports_dir, year, month, log_level)
            run_report("zap", nessus_scans, reports_dir, year, month, log_level)

        else:
            logger.error("Unknown report type specified.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Report generation failed for {report_type}: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")


def main():
    parser = argparse.ArgumentParser(description="ConMon Continuous Monitoring Script")
    parser.add_argument(
        "-y",
        "--year",
        type=int,
        help="Year for directory setup (default: current year)",
    )
    parser.add_argument(
        "-m",
        "--month",
        type=int,
        help="Month for directory setup (default: current month)",
    )
    parser.add_argument(
        "-r",
        "--report",
        choices=["daemons", "log4j", "summary", "work", "zap", "all"],
        required=True,
        help="Type of report to generate",
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

    # Use current year and month if not specified
    now = datetime.datetime.now()
    year = args.year if args.year else now.year
    month = args.month if args.month else now.month

    year_dir, month_dir, reports_dir = setup_dirs(year, month)

    nessus_scans = collect_nessus_scans(month_dir)

    if nessus_scans:
        run_report(args.report, nessus_scans, reports_dir, year, month, args.log_level)
    else:
        logger.warning("No Nessus scans to process.")


if __name__ == "__main__":
    main()
