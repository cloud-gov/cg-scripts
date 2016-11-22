#!/bin/bash

set -e

if [ "$#" -lt 4 ]; then
    printf "Usage:\n\n\t./cf-create-org.sh <AGENCY_NAME> <BIZ_ID> <SYSTEM_NAME> <NOTE> <MEMORY>\n\n"
    exit 1
fi

AGENCY_NAME=$1
BIZ_ID=$2
SYSTEM_NAME=$3
NOTE=$4

MEMORY="${5:-4G}"

QUOTA_NAME="${AGENCY_NAME}_${BIZ_ID}_${NOTE}"
ORG_NAME="${AGENCY_NAME}-${SYSTEM_NAME}"
NUMBER_OF_ROUTES=10
NUMBER_OF_SERVICES=10

# Step 0: Confirm the inputs.
# http://stackoverflow.com/a/226724/358804
printf "Create the following?\n\nQuota: $QUOTA_NAME\nOrg: $ORG_NAME\n\n"
select yn in "Yes" "No"; do
  case $yn in
    Yes ) break;;
    No ) exit 1;;
  esac
done

# Step 1: Create the quota
cf create-quota "$QUOTA_NAME" -m "$MEMORY" -r "$NUMBER_OF_ROUTES" -s "$NUMBER_OF_SERVICES" --allow-paid-service-plans

# Step 2: Create the org
cf create-org "$ORG_NAME" -q "$QUOTA_NAME"

# Step 3: Create the spaces
cf create-space -o "$ORG_NAME" dev
cf create-space -o "$ORG_NAME" staging
cf create-space -o "$ORG_NAME" prod
