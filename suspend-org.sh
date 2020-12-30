#!/bin/sh

# Deactivates an organization by setting its suspended status to true and stops
# all running applications in all spaces of the organization.

# Requires cf CLI version 7+ and jq to work.

set -e -x

if [ "$#" -ne 1 ]; then
  echo
  echo "Usage:"
  echo "   ./suspend-org.sh <org name>"
  echo

  exit 1
fi

# Check to see if the person has at least version 7 of the cf CLI; if not, let
# them know to upgrade and exit.
min_cf_version=7
cf_version=$(cf version | awk '{print $3}' | cut -c 1)

if [ "$cf_version" -lt "$min_cf_version" ]; then
  echo
  echo "You must update your cf CLI to at least version 7."
  echo "Please run: brew update && brew upgrade cf-cli@7"
  echo

  exit 1
fi

# Check to see if jq is available; if not, let them know to install it and exit.
if ! command -v jq &> /dev/null; then
  echo "jq could not be found; please make sure it is installed by running:"
  echo "brew install jq"

  exit 1
fi

org_name=$1
org_guid=$(cf org "${org_name}" --guid)

# Set the organization to suspended.
cf curl "/v3/organizations/${org_guid}" -X PATCH -d '{"suspended": true}'

# Get all of the application GUIDs in the organization.  This will retrieve all
# apps in all spaces within the org.
app_guids=$(cf curl "/v3/apps?organization_guids=${org_guid}" | jq -r '.resources[].guid')

# Stop each application in the organization.
for app_guid in $app_guids; do
  cf curl "v3/apps/${app_guid}/actions/stop" -X POST
done
