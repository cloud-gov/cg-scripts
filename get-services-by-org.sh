#!/bin/bash

if [ -z "$1" ]; then
  echo "organization GUID filter is required"
  exit 1
fi

ORG_GUIDS_FILTER="organization_guids=$1"
REQUEST_PATH="/v3/service_instances?$ORG_GUIDS_FILTER"

if [ -n "$2" ]; then
  REQUEST_PATH="$REQUEST_PATH&service_plan_names=$2"
fi

RESULTS=$(cf curl "$REQUEST_PATH" \
  | jq -c -r '.resources[] | {name: (.name), guid: (.guid), space_guid: (.relationships.space.data.guid)}')

for result in $RESULTS; do
  service_name=$(echo "$result" | jq -r '.name')
  service_guid=$(echo "$result" | jq -r '.guid')
  space_guid=$(echo "$result" | jq -r '.space_guid')
  space_name=$(cf curl "/v3/spaces/$space_guid" | jq -r '.name')
  echo "service: $service_name, guid: $service_guid, space: $space_name"
done
