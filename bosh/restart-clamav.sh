#!/bin/bash
#
# This script takes in a BOSH deployment name and restarts clamd and freshclam on each vm in that deployment

set -e

if [ "$#" -lt 1 ]; then
  echo
  echo "Usage:"
  echo "   ./restart-clamav.sh <deployment>"
  echo
  exit 1;
fi

deployment=$1

for instance in $(bosh -d $deployment vms --json | jq -r '.Tables[].Rows[].instance');
do
bosh -d $deployment ssh ${instance} sudo monit restart clamd freshclam;
done;
