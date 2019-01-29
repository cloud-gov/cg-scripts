#!/bin/sh

set -e -x

if [ "$#" -ne 1 ]; then
  echo
  echo "Usage:"
  echo "   ./activate-org.sh <org name>"
  echo
    exit 1
fi

org_name=$1
GUID=$(cf org "${org_name}" --guid)

cf curl "/v2/organizations/${GUID}" -X PUT -d '{"status":"active"}'

cf target -o "${org_name}"
for space in $(cf spaces "${org_name}" | tail -n +4); do
  cf t -s "${space}" > /dev/null
  for application in $(cf apps | tail -n +5); do
    cf start "${application}"
  done
done
