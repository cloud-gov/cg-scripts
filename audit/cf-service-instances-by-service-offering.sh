#!/bin/bash

set -e 

#if [ -z $1 ] || [ $1 == "--help" ]; then
function usage() {
  echo " "
  echo "Outputs service instance usage in a csv format."
  echo " "
	echo "Usage: $0 <service-offering-name>"
  echo " "
  echo -e "  service-offering-name: \t The name of the service offering to report on as shown in the marketplace"
  echo " "
  echo "Options: "
  echo " "
  echo "    $0 -h                         Display this help message."
  echo "    $0 -p <plan-name>             Query for instances of this plan from service-offering"
	exit 0
}

function printServiceInstances() {
  local svc_offering_name=$1
  local svc_offering_guid=$2
  local svc_plan_name=$3
  local svc_plan_guid=$4
  local svc_instances_json=$(cf curl "/v3/service_instances?service_plan_guids=${svc_plan_guid}&per_page=5000")
  local svc_instance_guids=$(echo "$svc_instances_json" | jq -r '.resources[].guid')
  for svc_instance_guid in $svc_instance_guids; do
    local svc_instance_json=$(echo "$svc_instances_json" | jq -r '.resources[] | select(.guid=="'"${svc_instance_guid}"'")')
    local svc_instance_name=$(echo "$svc_instance_json" | jq -r '.name')
    local created_at=$(echo "$svc_instance_json" | jq -r '.created_at') 
    local space_guid=$(echo "$svc_instance_json" | jq -r '.relationships.space.data.guid')
    local space_json=$(cf curl "/v3/spaces/${space_guid}")
    local space_name=$(echo "$space_json" | jq -r '.name')
    local org_guid=$(echo "$space_json" | jq -r '.relationships.organization.data.guid')
    local org_name=$(cf curl "/v3/organizations/${org_guid}" | jq -r '.name')
    local service_instance_guid=$(echo "$svc_instance_guid")
    echo "$svc_offering_name,$svc_plan_name,$svc_instance_name,$created_at,$org_name,$space_name,$service_instance_guid,$space_guid,$org_guid"
  done
  #echo "$svc_offering_name $svc_offering_guid $svc_plan_name $svc_plan_guid"
}

svc_plan_names=""


while getopts ":hp:" opt; do
  case ${opt} in
    h )
        usage 
        exit 0
        ;;
    p ) 
        svc_plan_names=$OPTARG
        ;;
    \? )
        echo "Invalid Option: $OPTARG" 1>&2
        usage 
        exit 1
        ;;
    : )
        echo "Invalid option: $OPTARG requires an argument" 1>&2
        usage 
        exit 1
        ;;
  esac
done
shift $((OPTIND -1))    

if [ $# -ne 1 ]; then
    echo "Please provide a service-offering-name" 1>&2
    usage 
    exit 1
fi

svc_offering_name=$1
echo "Offering name,Plan,Service Instance Name,Creation Date,Organization,Space,Service Instance GUID,Space GUID,Organization GUID"
svc_offering_guid=$(cf curl "/v3/service_offerings?names=${svc_offering_name}" | jq -r '.resources[].guid')
#echo "$svc_offering_name $svc_offering_guid"
svc_plans_json=$(cf curl "/v3/service_plans?service_offering_guids=${svc_offering_guid}")

if [ -z $svc_plan_names ]; then
  svc_plan_names=$(echo "$svc_plans_json" | jq -r '.resources[].name')
fi

for svc_plan_name in $svc_plan_names; do
  svc_plan_guid=$(echo "$svc_plans_json" | jq -r '.resources[] | select(.name=="'"${svc_plan_name}"'") | .guid')
  printServiceInstances $svc_offering_name $svc_offering_guid $svc_plan_name $svc_plan_guid
done

