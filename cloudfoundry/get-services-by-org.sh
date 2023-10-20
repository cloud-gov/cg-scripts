#!/bin/bash

if [ -z "$1" ]; then
  echo "organization GUID filter is required"
  exit 1
fi

ORG_GUIDS_FILTER="organization_guids=$1"
REQUEST_PATH="/v3/service_instances?$ORG_GUIDS_FILTER"

if [ -n "$2" ]; then
  SERVICE_PLAN_GUIDS=$(cf curl "/v3/service_plans?service_offering_names=$2" | jq -r '[.resources[].guid] | join(",")')
  REQUEST_PATH="$REQUEST_PATH&service_plan_guids=$SERVICE_PLAN_GUIDS"
fi

RESULTS=$(cf curl "$REQUEST_PATH" \
  | jq -c -r '.resources[] | {name: (.name), guid: (.guid), space_guid: (.relationships.space.data.guid)}')

echo "service,instance guid,space"
for result in $RESULTS; do
  service_name=$(echo "$result" | jq -r '.name')
  instance_guid=$(echo "$result" | jq -r '.guid')
  space_guid=$(echo "$result" | jq -r '.space_guid')
  space_name=$(cf curl "/v3/spaces/$space_guid" | jq -r '.name')
  echo "$service_name,$instance_guid,$space_name"
done
