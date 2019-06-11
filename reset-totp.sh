#!/bin/bash

set -eu

if [ "$#" -ne 2 ]; then
  script=$(basename "$0")
  echo "Usage: ${script} <deployment> <username>"
  exit 1
fi

deployment=$1
totp_username=$2

manifest=$(mktemp)
bosh -d ${deployment} manifest > "${manifest}"
address=$(bosh interpolate "${manifest}" --path /instance_groups/name=uaa/jobs/name=uaa/properties/uaadb/address)
password=$(bosh interpolate "${manifest}" --path /instance_groups/name=uaa/jobs/name=uaa/properties/uaadb/roles/name=cfdb/password)
rm "${manifest}"

psql "postgres://cfdb:${password}@${address}:5432/uaadb" -c "delete from totp_seed where username = '${totp_username}'"

echo "successfully reset the topt for ${totp_username}."

