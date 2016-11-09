#!/bin/bash

set -e

if [ "$#" -lt 5 ]; then
  printf "Usage:\n\n\t\$./cf-create-org.sh <AGENCY_NAME> <BIZ_ID> <SYSTEM_NAME> <NOTE> <MANAGER> <MEMORY>\n\n"
  exit 1
fi

AGENCY_NAME=$1
BIZ_ID=$2
SYSTEM_NAME=$3
NOTE=$4
MANAGER=$5

MEMORY="${6:-4G}"

if ! [[ $AGENCY_NAME =~ ^[a-zA-Z0-9]+$ ]]; then
  echo "AGENCY_NAME must contain only letters and numbers."
  exit 1
fi

if ! [[ $BIZ_ID =~ ^[a-zA-Z0-9_-]+$ ]]; then
  echo "BIZ_ID must contain only letters, numbers, underscores, and hyphens."
  exit 1
fi

if ! [[ $SYSTEM_NAME =~ ^[a-zA-Z0-9-]+$ ]]; then
  echo "SYSTEM_NAME must contain only letters, numbers, and hyphens."
  exit 1
fi

if ! [[ $NOTE =~ ^[a-zA-Z0-9_-]+$ ]]; then
  echo "NOTE must contain only letters, numbers, underscores, and hyphens."
  exit 1
fi

QUOTA_NAME="${AGENCY_NAME}_${BIZ_ID}_${NOTE}"
# uppercase
QUOTA_NAME=$(echo $QUOTA_NAME | awk '{print toupper($0)}')
ORG_NAME="${AGENCY_NAME}-${SYSTEM_NAME}"
# lowercase
ORG_NAME=$(echo $ORG_NAME | awk '{print tolower($0)}')
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

ADMIN=$(cf target | grep -i user | awk '{print $2}')

# Step 2: Create the org
cf create-org "$ORG_NAME" -q "$QUOTA_NAME"
# creator added by default, which is usually not desirable
cf unset-org-role "$ADMIN" "$ORG_NAME" OrgManager
cf set-org-role "$MANAGER" "$ORG_NAME" OrgManager

# Step 3: Create the spaces
declare -a spaces=("dev" "staging" "prod")
for SPACE in "${spaces[@]}"
do
  cf create-space -o "$ORG_NAME" "$SPACE"

  # creator added by default - undo
  cf unset-space-role "$ADMIN" "$ORG_NAME" "$SPACE" SpaceManager
  cf unset-space-role "$ADMIN" "$ORG_NAME" "$SPACE" SpaceDeveloper

  cf set-space-role "$MANAGER" "$ORG_NAME" "$SPACE" SpaceDeveloper
done

printf "Org created successfully. Target with\n\n\t\$ cf target -o $ORG_NAME\n\n"
