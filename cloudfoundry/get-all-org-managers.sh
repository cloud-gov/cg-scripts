#!/usr/bin/env bash

function get_org_managers {
  org_managers=$(cf org "$1" --guid \
    | xargs -I {} -n 1 cf curl "/v3/roles?organization_guids={}&include=user&types=organization_manager" \
    | jq -r '[.included.users[].username] | join(",")')
  echo "$1;$org_managers"
}

export -f get_org_managers

echo '"org name";"org managers"'

cf orgs \
  | tail -n +4 \
  | grep -v 'sandbox' \
  | xargs -I {} -n 1 bash -c 'get_org_managers "{}"'
