#!/bin/bash

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

function query_org {
  if [ -n "$ORG_GUID" ]; then
    ORG_NAME=$(cf curl "/v3/organizations/$ORG_GUID" | jq -r '.name')
    echo "org name: $ORG_NAME"
  fi
}

function query_space {
  if [ -n "$SPACE_GUID" ]; then
    SPACE_NAME=$(cf curl "/v3/spaces/$SPACE_GUID" | jq -r '.name')
    echo "space name: $SPACE_NAME"
  fi
}

function query_service {
  if [ -n "$INSTANCE_GUID" ]; then
    SERVICE_NAME=$(cf curl "/v3/service_instances/$INSTANCE_GUID"  | jq -r '.name')
    echo "service name: $SERVICE_NAME"
  fi
}

function query_rds {
  TAGS=$(aws rds describe-db-instances --db-instance-identifier "${1}" | jq -r '.DBInstances[0].TagList')

  ORG_GUID=$(echo "$TAGS" | jq -r '.[] | select(.Key=="Organization GUID") | .Value')
  SPACE_GUID=$(echo "$TAGS" | jq -r '.[] | select(.Key=="Space GUID") | .Value')
  INSTANCE_GUID=$(echo "$TAGS" | jq -r '.[] | select(.Key=="Instance GUID") | .Value')

  query_org "$ORG_GUID"
  query_space "$SPACE_GUID"
  query_service "$INSTANCE_GUID"
}

function query_s3 {
  TAGS=$(aws s3api get-bucket-tagging --bucket "${1}" | jq -r '.TagSet')

  ORG_GUID=$(echo "$TAGS" | jq -r '.[] | select(.Key=="Organization ID") | .Value')
  SPACE_GUID=$(echo "$TAGS" | jq -r '.[] | select(.Key=="Space ID") | .Value')
  INSTANCE_GUID="${1/cg-/}"

  query_org "$ORG_GUID"
  query_space "$SPACE_GUID"
  query_service "$INSTANCE_GUID"
}

if [ "${RESOURCE_TYPE}" == "rds" ]; then
  query_rds "$RESOURCE_IDENTIFIER"
elif [ "${RESOURCE_TYPE}" == "s3" ]; then
  query_s3 "$RESOURCE_IDENTIFIER"
else
  echo "Resource type: ${RESOURCE_TYPE} is not yet supported" >&2
fi
