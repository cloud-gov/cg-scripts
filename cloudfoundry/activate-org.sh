#!/bin/sh

# Activates an organization by setting its suspended status to false and starts
# all stopped applications in all spaces of the organization.

# Requires cf CLI version 7+ to work.

set -e -x

usage() {
  echo
  echo "Usage:"
  echo "   ./activate-org.sh <org name>"
  echo

  exit 1
}

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

org_name=$1
org_guid=$(cf org "${org_name}" --guid)

# Set the organization to not be suspended.
cf curl "/v3/organizations/${org_guid}" -X PATCH -d '{"suspended": false}'

# Display a note reminding the platform operator to inform the business unit or
# customer directly to restart their own apps, as we don't keep track of what
# was running prior to suspending an organization.
echo
echo "Organization ${org_name} has been reactivated."
echo "Please notify the customer that they must restart their applications."
echo
