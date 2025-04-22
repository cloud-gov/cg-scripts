#!/bin/bash

if [ "$#" -ne 4 ]; then
  echo
  echo "Usage:"
  echo "   update-plan-visibility.sh <list-of-org-names> <broker-name> <service-offering-name> <service-plan-name>"
  echo
  echo "where:"
  echo "   - <list-of-org-names>: comma-separated list of org names"
  echo "   - <broker-name>: name of broker providing service plan to update"
  echo "   - <service-offering-name>: name of service offering containing plan to update"
  echo "   - <service-plan-name>: service plan name to update"
  echo
  echo "Example:"
  echo "   update-plan-visibility.sh org-1,org-2 broker-1 offering1 plan1"
  exit 1
fi

ORG_NAMES=$1
BROKER_NAME=$2
SERVICE_OFFERING_NAME=$3
SERVICE_PLAN_NAME=$4

# FYI: doesn't handle pagination
ORGS=$(cf curl "/v3/organizations?names=$ORG_NAMES&per_page=5000" | jq '[.resources[] | {guid, name}]')

for plan_guid in $(cf curl "/v3/service_plans?service_broker_names=$BROKER_NAME&service_offering_names=$SERVICE_OFFERING_NAME" | jq --arg service_plan_name "$SERVICE_PLAN_NAME" -r '.resources[] | select(.name==$service_plan_name) | .guid'); do
  cf curl "/v3/service_plans/$plan_guid/visibility" \
    -X PATCH \
    -d "
      {
        \"type\": \"organization\",
        \"organizations\": $ORGS
      }
    "
done
