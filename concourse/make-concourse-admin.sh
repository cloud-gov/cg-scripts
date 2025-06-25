#!/bin/bash

set -e

if [ "$#" -lt 1 ]; then
  echo
  echo "Usage:"
  echo "  $ ./make-concourse-admin.sh [-r] <EMAIL_ADDRESS>"
  echo
  echo "  Options:"
  echo "     -r    :    Remove the user instead of add"
  echo
  exit 1;
fi
EMAIL=$BASH_ARGV
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

if $REMOVE; then
  echo -n "Removing user ${EMAIL}... "
  uaac member delete concourse.admin "${EMAIL}" || true
  uaac member delete concourse.apps "${EMAIL}" || true
  uaac user delete "${EMAIL}"
else
  echo -n "Adding user ${EMAIL}... "
  uaac curl -XPOST /Users -H"If-Match:*" -H"Accept:application/json" -H"Content-Type:application/json" -d\{\"userName\":\""${EMAIL}"\",\"emails\":[\{\"value\":\""${EMAIL}"\"\}],\"active\":true,\"verified\":true,\"origin\":\"gsa\"\}
  uaac member add concourse.admin "${EMAIL}" || true
fi

echo "DONE"
