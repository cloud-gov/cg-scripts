#!/usr/bin/env bash

set -euo pipefail
shopt -s inherit_errexit || true

main() {
  [[ $# -eq 2 ]] || usage "Expected two arguments, got $#"

  local user="$1"
  local org="$2"

  USER_GUID=$(cf curl "/v3/users?usernames=$user" | jq -r '.resources[0].guid // ""')

  if [[ -z "$USER_GUID" ]]; then
    echo "no user found for $user"
    exit 1
  fi

  ORGANIZATION_GUID=$(cf org "$org" --guid)

  # get all user roles for the org, including organization_user
  for role_guid in $(cf curl "/v3/roles?user_guids=$USER_GUID&organization_guids=$ORGANIZATION_GUID&per_page=5000" | jq -r '.resources[].guid'); do
    cf curl -X DELETE "/v3/roles/$role_guid"
  done
}

usage() {
  [[ $# -gt 0 ]] && echo "ERROR: $*"
  cat <<EOF
  USAGE: $(basename "$0") USER ORG SPACE

  Removes org and space roles for user.

  Examples:

    $(basename "$0") bob accounting dev
EOF
  exit 1
}

main "$@"
