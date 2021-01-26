#!/bin/bash

set -e

if [ "$#" -lt 1 ]; then
  echo
  echo "Usage:"
  echo "  $ ./make-pages-admin.sh [-r] <EMAIL_ADDRESS>"
  echo
  echo "  Options:"
  echo "     -r    :    Remove the user instead of add"
  echo 
  echo "  Be sure to run ./cg-scripts/uaa/login.sh prior to executing this script"
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

declare -a admin_groups=("pages.admin" "scim.read" "scim.write" )
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
