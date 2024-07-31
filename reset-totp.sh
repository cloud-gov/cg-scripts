#!/bin/bash

set -eu

if [ "$#" -ne 2 ]; then
  script=$(basename "$0")
  echo "Usage: ${script} <deployment> <username>"
  echo "If the username has a single quote in it, then wrap the value in double quotes (e.g. \"O'Test@gsa.gov\")"
  exit 1
fi

deployment=$1
totp_username=$2

manifest=$(mktemp)
bosh -d "${deployment}" manifest > "${manifest}"
address=$(bosh interpolate "${manifest}" --path /instance_groups/name=uaa/jobs/name=uaa/properties/uaadb/address)
password=$(bosh interpolate "${manifest}" --path /instance_groups/name=uaa/jobs/name=uaa/properties/uaadb/roles/name=cfdb/password)
rm "${manifest}"

# For usernames with single quotes (e.g. "O'Foobar@gsa.gov"), the single quotes have to be escaped for
# PostgreSQL by replacing them with double single quotes
escaped_username=${totp_username//\'/\'\'}
psql "postgres://cfdb:${password}@${address}:5432/uaadb" -c "delete from totp_seed where username = '${escaped_username}'"

echo "Successfully reset the totp for ${totp_username}. Please notify the user."
echo "NOTE: Username is case-sensitive - if the user is unable to reset, recheck capitalization"

