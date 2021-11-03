#!/bin/bash

#set -e
set -x

if [ "$#" -lt 5 ]; then
  printf "Usage:\n\n\t\$./cf-create-org.sh <AGENCY_NAME> <IAA_NUMBER> <SYSTEM_NAME> <POP_START> <POP_END> <MANAGER> <MEMORY>\n\n"
  exit 1
fi

AGENCY_NAME=$1
IAA_NUMBER=$2
SYSTEM_NAME=$3
POP_START=$4
POP_END=$5
MANAGER=$6

MEMORY="${7:-4G}"

ASG_TRUSTED_LOCAL_NETWORKS_INTERNAL_EGRESS="trusted_local_networks_egress"
ASG_PUBLIC_NETWORKS_EGRESS="public_networks_egress"

if ! [[ $AGENCY_NAME =~ ^[a-zA-Z0-9]+$ ]]; then
  echo "AGENCY_NAME must contain only letters and numbers."
  exit 1
fi

if ! [[ $IAA_NUMBER =~ ^[a-zA-Z0-9_\.-]+$ ]]; then
  echo "IAA_NUMBER must contain only letters, numbers, underscores, periods, and hyphens."
  exit 1
fi

if ! [[ $SYSTEM_NAME =~ ^[a-zA-Z0-9-]+$ ]]; then
  echo "SYSTEM_NAME must contain only letters, numbers, and hyphens."
  exit 1
fi

if ! [[ $POP_START =~ ^[0-9]{8}$ ]]; then
  echo "POP_START should be of the format YYYYMMDD."
  exit 1
fi

if ! [[ $POP_END =~ ^[0-9]{8}$ ]]; then
  echo "POP_END should be of the format YYYYMMDD."
  exit 1
fi

QUOTA_NAME_BASE="${AGENCY_NAME}_${IAA_NUMBER}_${POP_START}-${POP_END}"
# uppercase
QUOTA_NAME_BASE=$(echo "$QUOTA_NAME_BASE" | awk '{print toupper($0)}')
ORG_NAME="${AGENCY_NAME}-${SYSTEM_NAME}"
# lowercase
ORG_NAME=$(echo "$ORG_NAME" | awk '{print tolower($0)}')
NUMBER_OF_ROUTES=20
NUMBER_OF_SERVICES=20

# Add the date down to the second in order to avoid collisions for identical inputs
QUOTA_NAME="${QUOTA_NAME_BASE}-$(date '+%Y%m%d-%H:%M:%S')"

# Hash the name to obfuscate the origin of the quota from snooping users
HASHED_QUOTA_NAME=$(md5 -qs $QUOTA_NAME)

# Step 0: Confirm the inputs.
# http://stackoverflow.com/a/226724/358804
printf "Create the following?\n\nQuota: $HASHED_QUOTA_NAME\nOrg: $ORG_NAME\n\n"
select yn in "Yes" "No"; do
  case $yn in
    Yes ) break;;
    No ) exit 1;;
  esac
done

# Step 1: Check that we're logged into Concourse
CI_URL="${CI_URL:-"https://ci.fr.cloud.gov"}"
FLY_TARGET=$(fly targets | grep "${CI_URL}" | head -n 1 | awk '{print $1}')

if ! fly --target "${FLY_TARGET}" workers > /dev/null; then
  echo "Not logged in to concourse"
  exit 1
fi

# Step 2: Create the quota
cf create-quota "$HASHED_QUOTA_NAME" -m "$MEMORY" -r "$NUMBER_OF_ROUTES" -s "$NUMBER_OF_SERVICES" --allow-paid-service-plans

ADMIN=$(cf target | grep -i user | awk '{print $2}')

# Step 3: Create the org
cf create-org "$ORG_NAME" -q "$HASHED_QUOTA_NAME"
# creator added by default, which is usually not desirable
cf unset-org-role "$ADMIN" "$ORG_NAME" OrgManager
cf set-org-role "$MANAGER" "$ORG_NAME" OrgManager

# Step 4: Create the spaces
declare -a spaces=("dev" "staging" "prod")
for SPACE in "${spaces[@]}"
do
  declare -a spacetypes=("public" "internal" "private")
  for SPACETYPE in "${spacetypes[@]}"
  do
    cf create-space -o "$ORG_NAME" "$SPACE-$SPACETYPE"

    # creator added by default - undo
    cf unset-space-role "$ADMIN" "$ORG_NAME" "$SPACE-$SPACETYPE" SpaceManager
    cf unset-space-role "$ADMIN" "$ORG_NAME" "$SPACE-$SPACETYPE" SpaceDeveloper

    cf set-space-role "$MANAGER" "$ORG_NAME" "$SPACE-$SPACETYPE" SpaceDeveloper

    # Set space ASG
    if [[ $SPACETYPE = "public" ]]; then
      cf bind-security-group "$ASG_TRUSTED_LOCAL_NETWORKS_INTERNAL_EGRESS" "$ORG_NAME" --space "$SPACE-$SPACETYPE"
      cf bind-security-group "$ASG_PUBLIC_NETWORKS_EGRESS" "$ORG_NAME" --space "$SPACE-$SPACETYPE"
    fi

    if [[ $SPACETYPE = "internal" ]]; then
      cf bind-security-group "$ASG_TRUSTED_LOCAL_NETWORKS_INTERNAL_EGRESS" "$ORG_NAME" --space "$SPACE-$SPACETYPE"
    fi
  done
done


# deleting admin user from newly created org.
# https://github.com/cloudfoundry/cli/issues/781
USER_GUID=$(cf curl "/v3/users?usernames=${ADMIN}"| jq -r '.resources[] | .guid')
ORG_GUID=$(cf org "${ORG_NAME}" --guid)
ROLE_TO_DELETE_GUID=$(cf curl "/v3/roles?types=organization_user&organization_guids="${ORG_GUID}"&user_guids=${USER_GUID}" | jq -r '.resources[] | .guid')
# deleting role organization_user
cf curl -X DELETE "/v3/roles/${ROLE_TO_DELETE_GUID}"

# Hack: Trigger deployer account broker deploy to update organization whitelist
fly --target "${FLY_TARGET}" trigger-job --watch --job deploy-deployer-account-broker/push-broker-production
fly --target "${FLY_TARGET}" trigger-job --watch --job deploy-go-s3-broker/push-s3-broker-production

printf "Org created successfully. Target with\n\n\t\$ cf target -o $ORG_NAME\n\n"
