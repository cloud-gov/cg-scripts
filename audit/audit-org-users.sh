#!/bin/bash

function usage {
  echo -e "
  Usage

  ./$( basename "$0" ) <comma-separated list of orgs>

  Examples:

  ./$( basename "$0" ) org1,org2

  options:

  $0 -h                         Display this help message.

  Get all of the unique users in the specified organizations and all of those organizations' spaces.
  "
}

while getopts ":h" opt; do
  case ${opt} in
    h )
        usage
        exit 0
        ;;
    * )
        usage
        exit 0
        ;;
  esac
done
shift $((OPTIND -1))

orgs=${1//,/ }
export all_users=""

for org in $orgs; do
  printf "\norg: %s\n" "$org" >&2

  export all_org_users

  org_guid=$(cf org "$org" --guid)
  org_users=$(cf curl "/v3/organizations/$org_guid/users" | jq -r '[.resources[] | .username // empty]')
  
  for space_info in $(cf curl "/v3/spaces?organization_guids=$org_guid" | jq -r '.resources[] | .guid + "," + .name'); do
    IFS=',' read -r -a array <<< "$space_info"
    space_guid="${array[0]}"
    space_name="${array[1]}"
    
    space_users=$(cf curl "/v3/spaces/$space_guid/users" | jq -r '[.resources[] | .username // empty]')
    echo "all users for org $org, space: $space_name: $space_users" >&2
    all_org_users=$(echo -e "$org_users\n$space_users" | jq -s 'add | unique | sort')
  done

  echo "all users for org $org: $all_org_users" >&2
  all_users=$(echo -e "$all_users\n$all_org_users" | jq -s 'add | unique | sort')
done

echo "$all_users" | jq -r '.[]'
