#!/usr/bin/env python3
"""
Given a unix timestamp, list the prefix for files that might contain relevant logs
usage:
```shell
python3 logs-from-timestamp.py 1709655649692
```
s3://bucket/AWSlogs/[...]domains-2[...]20240301T0105
s3://bucket/AWSlogs/[...]domains-1[...]20240301T0105
s3://bucket/AWSlogs/[...]domains-0[...]20240301T0105

To sort and uniq output from a list of timestamps:
```shell
cat ~/Downloads/timestamps.txt | xargs -n1 python3 logs-from-timestamp.py > filenames.txt; cat filenames.txt | sort |uniq > filenames_filtered.txt
```
"""

import sys
import datetime

# hours to offset source time from utc
OFFSET_TIME = -5
ALB_NAMES = [
	# in the form 
	# "name.id"
]
REGION = ""
ACCOUNT_ID = ""
BUCKET = ""

def main():
	timestamp = int(sys.argv[1])
	timestamp = timestamp / 1000
	source_offset = datetime.timedelta(hours=OFFSET_TIME)
	utc_tz = datetime.timezone(offset=datetime.timedelta(hours=0))
	source_tz = datetime.timezone(offset=source_offset)
	target = datetime.datetime.fromtimestamp(int(timestamp), tz=source_tz)
	rounded = floor_to_five_minutes(target.astimezone())
	for name in ALB_NAMES:
		print(filename_from_datetime(rounded, name))	
	

def floor_to_five_minutes(dt):
	td = datetime.timedelta(minutes=(dt.minute % 5))
	return dt - td


def filename_from_datetime(target_dt, alb_name):
	s = f"s3://{BUCKET}/AWSLogs/{ACCOUNT_ID}/elasticloadbalancing/{REGION}" + \
		f"{ACCOUNT_ID}_elasticloadbalancing_{REGION}_app.{alb_name}_{target_dt.strftime('%Y%m%dT%H%M')}"
	return s


if __name__ == "__main__":
	main()

