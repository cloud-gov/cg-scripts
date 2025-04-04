#!/usr/bin/env python3
"""
Given WAF ELB output from a file, list the prefix for files that might contain relevant logs
usage:
$ python3 logs-from-timestamp.py waf filename
Where waf filename is WAF output based on UTC time

The output of this script is in the format:
s3://BUCKET/AWSLogs/ACCOUNT/elasticloadbalancing/REGION/YEAR/MONTH/DAY/ACCOUNT_elasticloadbalancing_REGION_app.
production-cloudfoundry-apps.ELB_TIMESTAMP
"""

import csv
import datetime
import os
import sys

# This script takes 1 argument
# csv filename
# It relies on two env vars: BUCKET_NAME and REGION
BUCKET = ""
REGION = ""

def main():
    file_name = str(sys.argv[1])
    content_lines = open(file_name).readlines()
    csv_reader = csv.DictReader(content_lines)
    for line in csv_reader:
        print(file_prefix_from_dict(line))

def floor_to_five_minutes(dt):
    td = datetime.timedelta(minutes=(dt.minute % 5))
    return dt - td


def file_prefix_from_dict(dict_line):
    BUCKET = os.getenv("BUCKET_NAME")
    REGION = os.getenv("REGION")
    ACCOUNT_ID = dict_line['httpSourceId'].split('-')[0]
    (YEAR,MONTH,DAY) = dict_line["@timestamp"].split()[0].split('-')
    alb_name = dict_line['httpSourceId'].split('/')[2]
    date_time: datetime = datetime.datetime.strptime(dict_line["@timestamp"], "%Y-%m-%d %H:%M:%S.%f")
    target_dt = floor_to_five_minutes(date_time)

    s = f"s3://{BUCKET}/AWSLogs/{ACCOUNT_ID}/elasticloadbalancing/{REGION}/{YEAR}/{MONTH}/{DAY}/" +\
    f"{ACCOUNT_ID}_elasticloadbalancing_{REGION}_app.production-cloudfoundry-apps.{alb_name}_{target_dt.strftime('%Y%m%dT%H%M')}"
    return s


if __name__ == "__main__":
    main()

