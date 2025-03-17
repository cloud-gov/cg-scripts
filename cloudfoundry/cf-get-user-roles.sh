#!/bin/bash

# import common functions

source "$(dirname "${BASH_SOURCE[0]}")/../lib/cf.sh"

# Grabs all cf org and space roles for a user

set -e

if [ "$#" -ne 1 ]; then
  echo
  echo "Usage:"
  echo "   ./cf-get-user-roles.sh <username>"
  echo

  exit 1
fi

# Check to see if the person has at least version 7 of the cf CLI; if not, let
# them know to upgrade and exit.
min_cf_version=7
cf_version=$(cf version | awk '{print $3}' | cut -c 1)

if [ "$cf_version" -lt "$min_cf_version" ]; then
  echo
  echo "You must update your cf CLI to at least version 7."
  echo "Please run: brew update && brew upgrade cf-cli@7"
  echo

  exit 1
fi

username=$1

printf "Retrieving all org and space roles for user: %s\n\n" "$username"

# get the user guid
user_guid=$(cf curl "/v3/users?usernames=$username" | jq -r '.resources[].guid')
if [[ -n "$user_guid" ]]; then
  printf "guid: %s\n" "$user_guid"
fi

# get all user roles and orgs
role_list=$(cf curl "/v3/roles?user_guids=${user_guid}&per_page=5000")

ORG_SPACE_RESULTS=$(echo "$role_list" | jq -r '
  .resources[] |
  .type + "," + (.relationships.organization.data.guid // "") + "," + (.relationships.space.data.guid // "")
')

for result in $ORG_SPACE_RESULTS; do
  role=$(echo "$result" | awk -F "," '{print $1}')

  ORG_GUID=$(echo "$result" | awk -F "," '{print $2}')
  org_name=$(query_org_name "$ORG_GUID")

  SPACE_GUID=$(echo "$result" | awk -F "," '{print $3}')
  space_name=$(query_space_name "$SPACE_GUID")

  output="$role:"
  if [[ -n "$org_name" ]]; then
    output="$output $org_name"
  fi
  if [[ -n "$space_name" ]]; then
    output="$output $space_name"
  fi
  echo "$output"
done
