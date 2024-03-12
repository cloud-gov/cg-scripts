#!/bin/bash
#
# This script takes in a BOSH deployment name and then queries BOSH for Credhub variables assoicated with the deployment.
# It then queries Credhub for the value and latest version created at date
# Finally it sorts the output with the newest/updated items at the top of the output

set -e

if [ "$#" -lt 1 ]; then
  echo
  echo "Please provide deployment name"
  echo
  exit 1;
fi

for V in $(bosh -d $1 variables | awk '{print $2}' ); do
	    echo "Value: $V Date updated: " $(credhub get -n $V -j | jq -r '.version_created_at')
done | sort -b -r -k5.1 -k5.2 -k5.3