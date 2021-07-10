#!/bin/bash

usage() {
  echo "Usage: "
  echo "  $0 <user-guid>"
  echo " "
  echo "  <user-guid>: The guid of the user to remove from all groups."
  echo " "
}

main() {
  if [[ ! $# -eq 1 ]]; then
    usage
    exit 1
  fi
  local user_guid=$1
  local group_guids=$(uaac curl /Groups | awk '/BODY/{y=1;next}y' | jq -r '.resources[] | select(.members[] | select(.value | contains("'"${user_guid}"'"))) | .id')
  for group_guid in $group_guids; do
    echo "Removing User: ${user_guid} from group: ${group_guid}"
    uaac curl -X DELETE /Groups/${group_guid}/members/${user_guid}
  done
}

main "$@"