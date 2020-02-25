#!/usr/bin/env bash

set -euo pipefail
shopt -s inherit_errexit

main() {
  if ! logged_in; then
    usage "Cannot authenticate. Maybe you forgot to run me via aws-vault?"
  fi

  local instances=$(aws rds describe-db-instances)
  local parameter_groups=$(aws rds describe-db-parameter-groups)

  used_pgs=$(jq -r '.DBInstances[].DBParameterGroups[].DBParameterGroupName' <<< "$instances" | sort -u)
  all_pgs=$(jq -r '.DBParameterGroups[].DBParameterGroupName' <<< "$parameter_groups" | sort -u)
  comm -23 <(echo "$all_pgs") <(echo "$used_pgs")
}

logged_in() {
  aws sts get-caller-identity > /dev/null 2>&1
}

usage() {
  cat <<EOF
  ERROR: $1

  USAGE: aws-vault exec profile $(basename "$0")

  Lists unused RDS parameter groups.  This was useful for removing said groups
  in order to reduce our usage so we didn't hit the AWS limit.
EOF
  exit 1
}

main "$@"
