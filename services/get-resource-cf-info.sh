#!/bin/bash

. "$(dirname "$0")/../lib/cf.sh"

function usage {
  echo -e "

  usage: $(basename "$0") <resource-type> <resource-identifier>

  Examples:

  ./$( basename "$0" ) s3 <bucket-name>
  ./$( basename "$0" ) rds <database-identifier>

  "
}

RESOURCE_TYPE="$1"
if [ -z "$RESOURCE_TYPE" ]; then
  echo "resource type is required as the first argument to script. valid values: rds, s3"
  usage
  exit 1
fi

RESOURCE_IDENTIFIER="$2"
if [ -z "$RESOURCE_IDENTIFIER" ]; then
  echo "resource identifier is required as the second argument to the script."
  usage
  exit 1
fi

function print_org {
  if [ -n "$1" ]; then
    echo "org name: $1"
  fi
}

function print_space {
  if [ -n "$1" ]; then
    echo "space name: $1"
  fi
}

function print_service_name {
  if [ -z "$1" ]; then
    echo "could not find service instance name for GUID $INSTANCE_GUID"
  else
    echo "service instance name: $1"
  fi
}

function print_cf_info {
  print_org "$(query_org_name "$ORG_GUID")"
  print_space "$(query_space_name "$SPACE_GUID")"
  print_service_name "$(query_service_instance_name "$INSTANCE_GUID")"
}

function query_rds {
  TAGS=$(aws rds describe-db-instances --db-instance-identifier "${1}" | jq -r '.DBInstances[0].TagList')

  ORG_GUID=$(echo "$TAGS" | jq -r '.[] | select(.Key=="Organization GUID") | .Value')
  SPACE_GUID=$(echo "$TAGS" | jq -r '.[] | select(.Key=="Space GUID") | .Value')
  INSTANCE_GUID=$(echo "$TAGS" | jq -r '.[] | select(.Key=="Instance GUID") | .Value')

  print_cf_info
}

function query_s3 {
  TAGS=$(aws s3api get-bucket-tagging --bucket "${1}" | jq -r '.TagSet')

  ORG_GUID=$(echo "$TAGS" | jq -r '.[] | select(.Key=="Organization ID" or .Key=="organizationGuid") | .Value')
  SPACE_GUID=$(echo "$TAGS" | jq -r '.[] | select(.Key=="Space ID" or .Key=="spaceGuid") | .Value')
  INSTANCE_GUID="${1/cg-/}"

  print_cf_info
}

if [ "${RESOURCE_TYPE}" == "rds" ]; then
  query_rds "$RESOURCE_IDENTIFIER"
elif [ "${RESOURCE_TYPE}" == "s3" ]; then
  query_s3 "$RESOURCE_IDENTIFIER"
else
  echo "Resource type: ${RESOURCE_TYPE} is not yet supported" >&2
fi
