#!/usr/bin/env bash

set -euo pipefail
shopt -s inherit_errexit || true

MAX_SPACE_ROLES=100
MAX_ORG_ROLES=20

main() {
  [[ $# -eq 2 ]] || usage "Expected two arguments, got $#"

  local user="$1"
  local org="$2"

  USER_GUID=$(cf curl "/v3/users?usernames=$user" | jq -r '.resources[0].guid // ""')

  if [[ -z "$USER_GUID" ]]; then
    echo "no user found for $user"
    exit 1
  fi

  if ! ORGANIZATION_GUID=$(cf org "$org" --guid); then
    echo "no org found for $org. Either it doesn't exist or something else went wrong"
    exit 1
  fi

  # get all space guids belonging to the org
  SPACE_GUIDS=$(cf curl "/v3/spaces?organization_guids=$ORGANIZATION_GUID" | jq -r '.resources[].guid')

  if [[ -n "$SPACE_GUIDS" ]]; then
    local space_guids_csv
    space_guids_csv=$(echo "$SPACE_GUIDS" | paste -sd, -)

    for role_guid in $(cf curl "/v3/roles?user_guids=$USER_GUID&space_guids=$space_guids_csv&per_page=$MAX_SPACE_ROLES" | jq -r '.resources[].guid'); do
      echo removing space role with: cf curl -X DELETE "/v3/roles/$role_guid"
      cf curl -X DELETE "/v3/roles/$role_guid"
    done
  fi

  # now remove all org-level roles for the user, including organization_user
  for role_guid in $(cf curl "/v3/roles?user_guids=$USER_GUID&organization_guids=$ORGANIZATION_GUID&per_page=$MAX_ORG_ROLES" | jq -r '.resources[].guid'); do
    echo removing org role with: cf curl -X DELETE "/v3/roles/$role_guid"
    # Let the above role removals propagate (sleep 1 was insufficent)
    sleep 5
    cf curl -X DELETE "/v3/roles/$role_guid"
  done
}

usage() {
  [[ $# -gt 0 ]] && echo "ERROR: $*"
  cat <<EOF
  USAGE: $(basename "$0") USER ORG

  Removes org and space roles for user.

  Examples:

    $(basename "$0") bob@cfo.gov accounting
EOF
  exit 1
}

main "$@"
