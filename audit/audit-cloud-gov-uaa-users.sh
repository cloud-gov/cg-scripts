#!/bin/bash

orgs=${1//,/ }
export all_admin_users=""

for org in $orgs; do
  printf "\norg: %s\n" "$org" >&2

  export all_org_users

  org_guid=$(cf org "$org" --guid)
  org_users=$(cf curl "/v3/organizations/$org_guid/users" | jq -r '[.resources[] |
    select(.username // empty | contains("gsa.gov")) |
    .username]')
  
  for space_guid in $(cf curl "/v3/spaces?organization_guids=$org_guid" | jq -r '.resources[].guid'); do
    space_users=$(cf curl "/v3/spaces/$space_guid/users" | jq -r '[.resources[] |
    select(.username // empty | contains("gsa.gov")) |
    .username]')
    echo "all cloud.gov admin users for org $org, space: $space_guid: $space_users" >&2
    all_org_users=$(echo -e "$org_users\n$space_users" | jq -s 'add | unique | sort')
  done

  echo "all cloud.gov admin users for org $org: $all_org_users" >&2
  all_admin_users=$(echo -e "$all_admin_users\n$all_org_users" | jq -s 'add | unique | sort')
done

echo "all cloud.gov admin users: $$all_admin_users" >&2

for user in $(echo "$all_admin_users" | jq -r '.[]'); do
  uaac user get "$user"
done
