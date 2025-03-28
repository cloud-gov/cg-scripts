#!/bin/bash

function usage {
cat >&2 <<EOM

Gets all service instances for the given organization name, service offering name, or list of GUIDs.
If a list of GUIDs is provided, the other two options will be ignored.

usage: $0 -o [org name] -s [service offering name] -i [comma-delimited list of GUIDs]

Examples:
  $0 -o org-name -s aws-elasticsearch
  $0 -o org-name -s aws-rds
  $0 -o org-name -s aws-elasticache-redis
  $0 -s custom-domain
  $0 -i guid1,guid2,guid3

EOM
}

while getopts ":hs:o:i:" opt; do
  case ${opt} in
    h )
      usage
      exit 0
      ;;
    o )
      ORGANIZATION_GUID=$(cf org "$OPTARG" --guid)
      ;;
    s )
      SERVICE_OFFERING=$OPTARG
      ;;
    i )
      INSTANCE_GUIDS=$OPTARG
      ;;
    * )
      echo "Invalid Option: $OPTARG"
      usage
      exit 1
      ;;
  esac
done
shift $((OPTIND -1))

if [ -z "$SERVICE_OFFERING" ] && [ -z "$ORGANIZATION_GUID" ] && [ -z "$INSTANCE_GUIDS" ]; then
  echo "You must provide instance GUIDs, a service offering name, or organization name"
  echo "as option(s) to the script. See the usage instructions below."
  usage
  exit 1
fi

REQUEST_PATH="/v3/service_instances?per_page=5000"

if [ -n "$ORGANIZATION_GUID" ] && [ -z "$INSTANCE_GUIDS" ]; then
  ORG_GUIDS_FILTER="organization_guids=$ORGANIZATION_GUID"
  REQUEST_PATH="$REQUEST_PATH&$ORG_GUIDS_FILTER"
fi

if [ -n "$SERVICE_OFFERING" ] && [ -z "$INSTANCE_GUIDS" ]; then
  SERVICE_PLAN_GUIDS=$(cf curl "/v3/service_plans?service_offering_names=$SERVICE_OFFERING" | jq -r '[.resources[].guid] | join(",")')
  REQUEST_PATH="${REQUEST_PATH}&service_plan_guids=$SERVICE_PLAN_GUIDS"
fi

if [ -n "$INSTANCE_GUIDS" ]; then
  REQUEST_PATH="$REQUEST_PATH&guids=$INSTANCE_GUIDS"
fi

RESULTS=$(cf curl "$REQUEST_PATH" \
  | jq -c -r '.resources[] | {name: (.name), guid: (.guid), space_guid: (.relationships.space.data.guid)}')

lookup_results=$(mktemp)
echo "Service Instance GUID,Service Instance Name,Organization,Space"
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
  
  echo "$instance_guid,$service_name,$org_name,$space_name"
done

rm "$lookup_results"
