#!/bin/bash
set -e -o pipefail

# import common functions
. "$(dirname "$0")/../lib/common.sh"

function usage {

cat >&2 <<EOM
usage: $(basename "$0") -i iaa -o org_name -m manager[,origin] -m manager[,origin] -q quota_in_GB(8)

examples:
  $0 -i CFXXX250001-0002 -o dept-office-system -m pickle@gsa.gov,gsa.gov -m gherkin@dept.gov -q 8
  $0 -i CFXXX250001-0001 -o dept-office-another -m okra@dept.gov -q 16
EOM
}

function check_auth {
  CI_URL="${CI_URL:-"https://ci.fr.cloud.gov"}"
  FLY_TARGET=$(fly targets | grep "${CI_URL}" | head -n 1 | awk '{print $1}')

  if ! fly --target "${FLY_TARGET}" workers > /dev/null; then
    raise "Not logged in to Concourse: $CI_URL"
  fi

  cf oauth-token 1>/dev/null || raise "Not logged in to Cloud.gov's Cloud Foundry"
}

MEMORY_QUOTA=8

while getopts ":hi:m:o:q:" opt; do
  case ${opt} in
    h )
      usage
      exit 0 
      ;;
    i )
      IAA=$OPTARG;;
    m )
      MANAGERS+=("$OPTARG");;
    o )
      ORG_NAME=$OPTARG;;
    q )
      MEMORY_QUOTA=$OPTARG;;
    \? ) 
      raise "Invalid option: $OPTARG";;
    : )
      raise "Invalid option: $OPTARG requires an argument"
      ;;
  esac
done
shift $((OPTIND-1))

# Make sure we're logged in
check_auth 

[[ -z $IAA ]] && ( usage ; raise "'-i iaa' is REQUIRED" )
[[ -z $ORG_NAME  ]] && ( usage ; raise "'-o org_name' is REQUIRED" )
[[ -z "${MANAGERS[0]}" ]] && ( usage ; raise "'-m manager_email' is REQUIRED at least once" )

set -u # exit on unbound variables

if ! [[ $ORG_NAME =~ ^[a-zA-Z0-9-]+$ ]]; then
  raise "ORG_NAME must contain only letters, numbers, and hypens."
fi
if ! [[ $IAA =~ ^[a-zA-Z0-9_\.-]+$ ]]; then
  raise "IAA must contain only letters, numbers, underscores, periods, and hyphens."
fi

# Add epoch time to avoid naming collisions
NOW=$(date '+%s')
# Hash the name to obfuscate the origin of the quota from snooping users
QUOTA_NAME=$( echo "${ORG_NAME}_${IAA}_${NOW}" | tr '[:lower:]' '[:upper:]' | md5 -q )
# Add the "customer-" prefex
QUOTA_NAME="customer-${QUOTA_NAME}"
# lowercase the org_name
ORG_NAME=$(echo "$ORG_NAME" | tr '[:upper:]' '[:lower:]')

# Step 2: Create the quota
NUMBER_OF_ROUTES=20
NUMBER_OF_SERVICES=20
cf create-quota "$QUOTA_NAME" -m "$MEMORY_QUOTA"G -r "$NUMBER_OF_ROUTES" -s "$NUMBER_OF_SERVICES" --allow-paid-service-plans

# Step 3: Create the org
cf org "$ORG_NAME" 1>/dev/null && \
  ( printf "\nFound org, undoing\n\n" && cf delete-quota "$QUOTA_NAME" -f && raise "Org $ORG_NAME already exists" )
cf create-org "$ORG_NAME" -q "$QUOTA_NAME" 
cf set-label org "$ORG_NAME" org-type=customer 

# Step 4: Create the spaces
# We use `cf curl` so we don't get added as SpaceManagers
ORG_GUID=$(cf org --guid "$ORG_NAME")

declare -a spaces=("dev" "staging" "prod")
for SPACE in "${spaces[@]}"
do
  data=$(cat<<EOM
  { "name": "$SPACE", "relationships": { "organization": { "data": { "guid": "$ORG_GUID" } } } }
EOM
)
  echo Creating space: "$SPACE"
  eval cf curl "/v3/spaces" -X POST -d \'"$data"\'
done

# Step: Add the managers
for manager_info in "${MANAGERS[@]}"; do
  IFS=\,; read -ra fields <<< "$manager_info"
  if [ ${#fields[@]} = 2 ]; then 
    MANAGER=${fields[0]}
    ORIGIN=${fields[1]}
    echo Setting up manager "$MANAGER" with origin "$ORIGIN"
      cf set-org-role "$MANAGER" "$ORG_NAME" OrgManager --origin "$ORIGIN"
    for SPACE in "${spaces[@]}"; do
      cf set-space-role "$MANAGER" "$ORG_NAME" "$SPACE" SpaceDeveloper --origin "$ORIGIN"
    done
   else 
    MANAGER=${fields[0]}
    echo Setting up manager "$MANAGER" with no origin
      cf set-org-role "$MANAGER" "$ORG_NAME" OrgManager 
    for SPACE in "${spaces[@]}"; do
      cf set-space-role "$MANAGER" "$ORG_NAME" "$SPACE" SpaceDeveloper 
    done
  fi
done

# Hack: Trigger deployer account broker deploy to update organization whitelist
echo fly --target "${FLY_TARGET}" trigger-job --job deploy-uaa-credentials-broker/push-broker-"${CF_INSTALL:=production}"
echo fly --target "${FLY_TARGET}" trigger-job --job deploy-go-s3-broker/push-s3-broker-"${CF_INSTALL}"

printf 'Org created successfully. Target with\n\n\t\$ cf target -o %s\n\n' "$ORG_NAME"

echo "To undo this work run: "
echo "  cf delete-org -f $ORG_NAME"
echo "  cf delete-quota -f $QUOTA_NAME"
