#!/bin/bash

##
# Get the memory quota and usage for a specific organization.
# 
# Example usage:
# ~$ ./get-org-mem-usage.sh sandbox-gsa

# Org name: sandbox-gsa
# GUID: 70a1c8e4-6555-44ff-9ed0-57711c90104f
# Quota (GB): 50
# Usage (GB): 8
#
## 

if [[ ! $(which jq) ]]; then
  echo "Error: You must have the jq utility installed to run this script. https://stedolan.github.io/jq/" >&2
  exit 1
fi

if [ -z "$1" ]
  then
    echo "You must supply an org name"
    exit 1
fi

# Get organization details
org=$(cf curl v3/organizations/?names=$1)

# Get the guid for the organization
guid=$(echo $org | jq -j '.resources[] | .guid')

# Get the quota for the organization.
quota=$(echo $org | jq -j '.resources[] | .relationships | .quota | .data | .guid')

# Get the memory portion of the quota.
total_memory=$(cf curl v3/organization_quotas/$quota | jq '.apps | .total_memory_in_mb')

# Get the current memory in use.
memory_in_use=$(cf curl v3/organizations/$guid/usage_summary | jq '.usage_summary | .memory_in_mb');

# Display summary
echo ""
echo "Org name: $1"
echo "GUID: $guid"
echo "Quota (GB): "$(($total_memory/1024))
echo "Usage (GB): "$(($memory_in_use/1024))
echo ""