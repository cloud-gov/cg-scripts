#!/bin/bash

function usage {
cat >&2 <<EOM

Gets all service instances for the given organization GUID

usage: $0 <org guid value> [service offering name]

Examples:
  $0 org-guid-123 aws-elasticsearch
  $0 org-guid-123 aws-rds
  $0 org-guid-123 aws-elasticache-redis

EOM
}

while getopts ":h" opt; do
  case ${opt} in
    h )
      usage
      exit 0
      ;;
    * )
      echo "Invalid Option: $OPTARG"
      usage
      exit 1
      ;;
  esac
done
shift $((OPTIND -1))

if [ -z "$1" ]; then
  echo "organization GUID filter is required"
  usage
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
