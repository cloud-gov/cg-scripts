#!/usr/bin/env bash

set -euo pipefail
shopt -s inherit_errexit || true

main() {
  [[ $# -eq 3 ]] || usage "Expected three arguments, got $#"

  local user="$1"
  local org="$2"
  local space="$3"

  cf unset-org-role "$user" "$org" OrgManager
  for space_role in SpaceManager SpaceDeveloper SpaceAuditor; do
    cf unset-space-role "$user" "$org" "$space" "$space_role"
  done

  echo "Org users:"
  cf org-users "$org"

  echo "Space users:"
  cf space-users "$org" "$space"
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
