#!/bin/sh

set -e -x

if [ "$#" -ne 1 ]; then
  echo
  echo "Usage:"
  echo "   ./suspend-org.sh <org name>"
  echo
    exit 1
fi

GUID=$(cf org $1 --guid)

cf curl /v2/organizations/$GUID -X PUT -d '{"status":"suspended"}'

for route in $(cf curl /v2/routes?q=organization_guid:$GUID | jq -r .resources[].metadata.guid)
do
  cf curl -X DELETE /v2/routes/$route?recursive=true
done
