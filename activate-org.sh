#!/bin/sh

# Activates an organization by setting its suspended status to false and starts
# all stopped applications in all spaces of the organization.

# Requires cf CLI version 7+ to work.

set -e -x

if [ "$#" -ne 1 ]; then
  echo
  echo "Usage:"
  echo "   ./activate-org.sh <org name>"
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

org_name=$1
GUID=$(cf org "${org_name}" --guid)

# Set the organization to not be suspended.
cf curl "/v3/organizations/${GUID}" -X PATCH -d '{"suspended": false}'

cf target -o "${org_name}"

# Space names can contain spaces, so a for loop won't work as it'll break to
# the next line upon the first whitespace character it reaches, not just a
# newline character.  A while loop processes a whole line.
cf spaces | tail -n +4 | while read -r space; do
  cf t -s "${space}" > /dev/null

  # The output of running `cf apps` includes more information than just the
  # application name, which is the only thing we need.
  for application in $(cf apps | tail -n +4 | awk '{ print $1 }'); do
    cf start "${application}"
  done
done
