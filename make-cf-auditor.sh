#!/bin/bash

set -e

if [ "$#" -lt 1 ]; then
  echo
  echo "Usage:"
  echo "  $ ${0} [-r] <EMAIL_ADDRESS>"
  echo
  echo "  Options:"
  echo "     -r    :    Remove the user instead of add"
  echo
  exit 1;
fi
USER=$BASH_ARGV
REMOVE=false

while getopts ":r" opt; do
  case $opt in
    r)
      REMOVE=true
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1;
      ;;
  esac
done

if ! hash uaac 2>/dev/null; then
  gem install cf-uaac
fi

declare -a admin_groups=("cloud_controller.global_auditor" "scim.read" "admin_ui.user")
if $REMOVE; then
  for group in ${admin_groups[@]}
  do
    echo -n "Removing user from group ${group}... "
    uaac member delete "${group}" "${USER}" || true
  done
else
  for group in ${admin_groups[@]}
  do
    echo -n "Adding user to group ${group}... "
    uaac member add "${group}" "${USER}" || true
  done
fi

echo "DONE"
