#!/bin/bash

set -e

if [ "$#" -lt 1 ]; then
  echo
  echo "Usage:"
  echo "  $ ./add-user.sh <EMAIL_ADDRESS>"
  echo
  exit 1;
fi

if ! hash uaac 2>/dev/null; then
  echo -n "uaac must be installed"
  exit 1
fi

EMAIL=$1
ORIGIN=$(awk -F '@' '{print $2}' <<< "$EMAIL")

echo -n "Adding user ${EMAIL}... "
uaac curl \
  -X POST /Users \
  -H "If-Match:*" \
  -H "Accept:application/json" \
  -H "Content-Type:application/json" \
  -d \{\"userName\":\""${EMAIL}"\",\"emails\":[\{\"value\":\""${EMAIL}"\"\}],\"active\":true,\"verified\":true,\"origin\":\""${ORIGIN}"\"\}

