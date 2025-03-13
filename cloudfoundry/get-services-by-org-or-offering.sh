#!/bin/bash

function usage {
cat >&2 <<EOM

Gets all service instances for the given organization GUID and/or service offering

usage: $0 -o [org guid value] -s [service offering name]

Examples:
  $0 -o org-guid-123 -s aws-elasticsearch
  $0 -o org-guid-123 -s aws-rds
  $0 -o org-guid-123 -s aws-elasticache-redis
  $0 -s custom-domain

EOM
}

while getopts ":hs:o:" opt; do
  case ${opt} in
    h )
      usage
      exit 0
      ;;
    o )
      ORGANIZATION_GUID=$OPTARG
      ;;
    s )
      SERVICE_OFFERING=$OPTARG
      ;;
    * )
      echo "Invalid Option: $OPTARG"
      usage
      exit 1
      ;;
  esac
done
shift $((OPTIND -1))

REQUEST_PATH="/v3/service_instances?per_page=5000"

if [ -n "$ORGANIZATION_GUID" ]; then
  ORG_GUIDS_FILTER="organization_guids=$ORGANIZATION_GUID"
  REQUEST_PATH="$REQUEST_PATH&$ORG_GUIDS_FILTER"
fi

if [ -n "$SERVICE_OFFERING" ]; then
  SERVICE_PLAN_GUIDS=$(cf curl "/v3/service_plans?service_offering_names=$SERVICE_OFFERING" | jq -r '[.resources[].guid] | join(",")')
  REQUEST_PATH="${REQUEST_PATH}&service_plan_guids=$SERVICE_PLAN_GUIDS"
fi

RESULTS=$(cf curl "$REQUEST_PATH" \
  | jq -c -r '.resources[] | {name: (.name), guid: (.guid), space_guid: (.relationships.space.data.guid)}')

lookup_results=$(mktemp)
echo "Service Instance Name,Service Instance GUID,Organization,Space"
for result in $RESULTS; do
  service_name=$(echo "$result" | jq -r '.name')
  instance_guid=$(echo "$result" | jq -r '.guid')
  space_guid=$(echo "$result" | jq -r '.space_guid')
  
  existing_space_result=$(grep "^$space_guid" "$lookup_results")
  if [ -n "$existing_space_result" ]; then
    space_name=$(echo "$existing_space_result" | awk -F ',' '{print $2}')
    org_guid=$(echo "$existing_space_result" | awk -F ',' '{print $3}')
  else
    space_info=$(cf curl "/v3/spaces/$space_guid")
    space_name=$(echo "$space_info" | jq -r '.name')
    org_guid=$(echo "$space_info" | jq -r '.relationships.organization.data.guid')
    echo "$space_guid,$space_name,$org_guid" >> "$lookup_results"
  fi
  
  existing_org_result=$(grep "^$org_guid" "$lookup_results")
  if [ -n "$existing_org_result" ]; then
    org_name=$(echo "$existing_org_result" | awk -F ',' '{print $2}')
  else    
    org_name=$(cf curl "/v3/organizations/$org_guid" | jq -r '.name')
    echo "$org_guid,$org_name" >> "$lookup_results"
  fi      
  
  echo "$service_name,$instance_guid,$org_name,$space_name"
done

rm "$lookup_results"
