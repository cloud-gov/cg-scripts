#!/bin/bash

TAGS=$(aws rds describe-db-instances --db-instance-identifier "${1}" | jq -r '.DBInstances[0].TagList')
ORG_GUID=$(echo "$TAGS" | jq -r '.[] | select(.Key=="Organization GUID") | .Value')
SPACE_GUID=$(echo "$TAGS" | jq -r '.[] | select(.Key=="Space GUID") | .Value')
INSTANCE_GUID=$(echo "$TAGS" | jq -r '.[] | select(.Key=="Instance GUID") | .Value')

if [ -n "$ORG_GUID" ]; then
  ORG_NAME=$(cf curl "/v3/organizations/$ORG_GUID" | jq -r '.name')
  echo "org name: $ORG_NAME"
fi

if [ -n "$SPACE_GUID" ]; then
  SPACE_NAME=$(cf curl "/v3/spaces/$SPACE_GUID" | jq -r '.name')
  echo "space name: $SPACE_NAME"
fi

if [ -n "$INSTANCE_GUID" ]; then
  SERVICE_NAME=$(cf curl "/v3/service_instances/$INSTANCE_GUID"  | jq -r '.name')
  echo "service name: $SERVICE_NAME"
fi
