#!/bin/bash

set -e

# description: This script gets the latest users on the platform. The resulting CSV
# will still need to be verified and modified to remove none email addresses or empty
# fields.
# usage: ./cf-get-recent-users.sh [optional_page_number]


if ! [[ $( which cf ) ]]; then
  echo "You must have \`cf\` installed in your path."
  echo "If you're on a Mac, use Homebrew: \`brew install cf\`."
  exit 99
fi

if ! [[ $( which jq ) ]]; then
  echo "You must have \`jq\` installed in your path."
  echo "If you're on a Mac, use Homebrew: \`brew install jq\`."
  exit 98
fi

if [[ ! -a emails.csv ]]; then
  echo "Creating emails.csv file in the current directory"
  touch emails.csv
  echo "created_at,username" > emails.csv
fi

if [[ ! -z "$1" ]]; then
  page_number=$1
else
  page_number=1
fi

cf curl \
  "/v2/users?order-direction=desc&results-per-page=100&page=${page_number}" | \
jq -r \
  '.resources[] | [.metadata.created_at,.entity.username] | @csv' \
>> emails.csv
