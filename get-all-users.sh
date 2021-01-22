#!/bin/sh

# Retrieves all users in the system and outputs a CSV file.

# Requires cf CLI version 7+ and jq to work.

# NOTE:  Only works if there are 5,000 or less users in the system at this time.

# USAGE:
#    ./get-all-users.sh [-csv -nh]
#    -csv    Outputs data to a CSV file instead of STDOUT.
#    -nh     Excludes a header row from being created in a CSV file.

# TODOS:
# - Use pagination to account for the 5,000 record limit and use smaller pages.
# - Convert this script to Python for more flexibility in the future.

set -e

# Check to see if the person has at least version 7 of the cf CLI; if not, let
# them know to upgrade and exit.
MIN_CF_VERSION=7
CURRENT_CF_VERSION=$(cf version | awk '{print $3}' | cut -c 1)

if [ "$CURRENT_CF_VERSION" -lt "$MIN_CF_VERSION" ]; then
  echo
  echo "You must update your cf CLI to at least version 7."
  echo "Please run: brew update && brew upgrade cf-cli@7"
  echo

  exit 1
fi

# Retrieve command line arguments for parsing options.
PRINT_HEADER=1
OUTPUT_FILE=0

while [[ $# -gt 0 ]]
do
  KEY="$1"

  case $KEY in
      -csv|--output-csv)
      OUTPUT_FILE=1
      echo "Retrieving all user data..."
      shift # past argument
      ;;
      -nh|--no-header)
      PRINT_HEADER=0
      shift # past argument
      ;;
  esac
done

# Retrieve all users as JSON.
USER_JSON=$(cf curl '/v3/users?per_page=5000')

# Retrieve the information from the JSON output in CSV format.
# This information is sorted first by username, then by origin, to help with
# grouping.  Records without usernames are stripped out as they are not actual
# users, they're system accounts and used internally.
CSV_OUTPUT=$(echo $USER_JSON | jq -r '.resources |= sort_by(.username) | .resources |= sort_by(.origin) | .resources[] | select(.username != "") | [ .username, .presentation_name, .guid, .created_at, .origin ] | @csv')

# Check if the data should be output STDOUT; otherwise write data to a CSV file.
if [ $OUTPUT_FILE -eq 0 ]; then
  echo $CSV_OUTPUT
else
  # Check if a header row is desired; otherwise, don't create one.
  if [ $PRINT_HEADER -eq 1 ]; then
    echo '"username","presentation name","guid","created at","origin"' > all-users.csv
  else
    > all-users.csv
  fi

  echo $CSV_OUTPUT >> all-users.csv
  echo "...all-users.csv created successfully."
fi
