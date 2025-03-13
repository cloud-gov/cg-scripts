#!/bin/sh

# Deactivates an organization by setting its suspended status to true and optionally stops
# all running applications in all spaces of the organization. 

# Requires cf CLI version 7+ and jq to work.

set -e -x

usage() {
  echo
  echo "Usage:"
  echo "   ./suspend-org.sh -k <org name>"
  echo
  echo "  Options:"
  echo "     -k    :    Keep apps running, do not stop them"
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

# Check to see if jq is available; if not, let them know to install it and exit.
if ! command -v jq > /dev/null 2>&1; then
  echo "jq could not be found; please make sure it is installed by running:"
  echo "brew install jq"

  exit 1
fi


STOP_APPS=true

while getopts ":k" opt; do
  case $opt in
    k)
      STOP_APPS=false
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1;
      ;;
  esac
done
shift $((OPTIND -1))

org_name=$1
if [ -z "$org_name" ]; then
  echo "org name is required as first argument"
  set +x
  usage
fi

org_guid=$(cf org "${org_name}" --guid)

# Set the organization to suspended.
cf curl "/v3/organizations/${org_guid}" -X PATCH -d '{"suspended": true}'

# Stop each application in the organization.
if $STOP_APPS; then
  # Get all of the application GUIDs in the organization.  This will retrieve all
  # apps in all spaces within the org.
  app_guids=$(cf curl "/v3/apps?organization_guids=${org_guid}" | jq -r '.resources[].guid')

  for app_guid in $app_guids; do
    cf curl "/v3/apps/${app_guid}/actions/stop" -X POST
  done
fi
