#!/usr/bin/env bash

ORGS=$1

function get_org_users {
  org_users=$(cf org "$1" --guid \
    | xargs -I {} -n 1 cf curl "/v3/organizations/{}/users" \
    | jq -r '[.resources[] | .username // empty] | join(",")')
  echo "$1;$org_users"
}

export -f get_org_users

echo '"org name";"org users"'

if [[ -z "$ORGS" ]]; then
  cf orgs \
      | tail -n +4 \
      | grep -v 'sandbox\|arsalan-haider\|mark-boyd\|3pao\|test-\|system\|david-anderson\|cf\|cloud-gov\|tech-talk' \
      | xargs -I {} -n 1 bash -c 'get_org_users "{}"'
else
  get_org_users "$ORGS"  
fi

