#!/bin/sh

# Retrieves all users in the system and outputs a CSV file.

# Requires cf CLI version 7+ and jq to work.

# NOTE:  Only works if there are 5,000 or less users in the system at this time.

set -e -x

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

# Retrieve all users as JSON.
cf curl '/v3/users?per_page=5000' > all-users.json

# Create a CSV file with a header row.
echo '"username","presentation name","guid","created at","origin"' > all-users.csv

# Append all of the user data into the CSV file.
# This information is sorted first by username, then by origin, to help with
# grouping.  Records without usernames are stripped out as they are not actual
# users, they're system accounts and used internally.
cat all-users.json | jq -r '.resources |= sort_by(.username) | .resources |= sort_by(.origin) | .resources[] | select(.username != "") | [ .username, .presentation_name, .guid, .created_at, .origin ] | @csv' >> all-users.csv
