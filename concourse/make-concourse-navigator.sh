#!/bin/bash

set -e

if [ "$#" -lt 1 ]; then
  echo
  echo "Usage:"
  echo "  $ ./make-concourse-navigator.sh [-r] <EMAIL_ADDRESS>"
  echo
  echo "  Options:"
  echo "     -r    :    Remove the user instead of add"
  echo
  exit 1;
fi
EMAIL=$BASH_ARGV
REMOVE=false

SCOPE=concourse.apps

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

if ! uaac group get ${SCOPE} &>/dev/null; then
  echo "Scope ${SCOPE} does not exist. Did you target the correct UAA?"
  exit 1;
fi


if $REMOVE; then
  echo -n "Removing user ${EMAIL}... "
  uaac member delete ${SCOPE} "${EMAIL}" || true
  uaac user delete "${EMAIL}"
else
  # create user if not exist
  if ! uaac user get ${EMAIL} &>/dev/null; then
    echo -n "Adding user ${EMAIL}... "
    uaac curl -XPOST /Users -H"If-Match:*" -H"Accept:application/json" -H"Content-Type:application/json" -d\{\"userName\":\""${EMAIL}"\",\"emails\":[\{\"value\":\""${EMAIL}"\"\}],\"active\":true,\"verified\":true,\"origin\":\"gsa\"\}
  fi

  uaac member add ${SCOPE} "${EMAIL}" || true
fi

echo "DONE"
