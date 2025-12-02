#!/usr/bin/env bash

set -euo pipefail
shopt -s inherit_errexit || true

main() {
  [[ $# -eq 2 ]] || usage "Expected two arguments, got $#"

  local user="$1"
  local org="$2"

  cf unset-org-role "$user" "$org" OrgManager

  echo "Org users:"
  cf org-users "$org"

  for space in $(cf curl "/v3/spaces?organization_guids=$(cf org ustda-website --guid)" | jq -r '.resources[].name'); do
    for space_role in SpaceManager SpaceDeveloper SpaceAuditor; do
      cf unset-space-role "$user" "$org" "$space" "$space_role"
    done

    echo "Space users:"
    cf space-users "$org" "$space"
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
