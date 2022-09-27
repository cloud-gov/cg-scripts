#!/bin/bash

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

echo "Retrieving all org and space roles for user: $username"

#get the user guid
user_guid=$(cf curl "/v3/users?usernames=$username" | jq -r '.resources[].guid')

#get all user roles and orgs
role_list=$(cf curl "/v3/roles?user_guids=${user_guid}&per_page=5000")

headers=$(echo "role", "org_uuid", "space_uuid")
formatted_list=$(echo $role_list | jq -r '.resources[] | [.type, .relationships.organization.data.guid // "null", .relationships.space.data.guid // "null"] | @csv')

#output a nice table
echo -e "$headers\\n$formatted_list" | column -t -s,