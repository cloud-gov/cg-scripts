#!/bin/bash

set -e

# Counts the number of current active sandboxes in the platform.

# An active sandbox is defined as any user's sandbox space with 1 or more
# running apps in it.

# We can determine this by using the cf CLI and CAPI to retrieve all sandbox
# orgs, then filter a list of all apps with those corresponding org GUIDs.

if [[ $1 == "--help" ]]; then
  echo " "
  echo "Counts the number of current active sandboxes in the platform."
  echo " "
	echo "Usage: get-active-sandbox-and-space-count [START_DATE] [END_DATE]"
  echo " "
  echo -e "  START_DATE: \t A date to limit finding active sandboxes at or after the provided date in YYYY-MM-DD format."
  echo -e "  END_DATE: \t A date to limit finding active sandboxes at or before the provided date in YYYY-MM-DD format."
  echo " "
	exit 0
fi

start_date=$1
end_date=$2
extra_params=""

echo "Getting total counts of active sandboxes and sandbox spaces..."

# If a start date was given, filter for sandboxes created at the start date and
# after, starting at the very beginning of the day.
if [ $start_date ]; then
    extra_params="${extra_params}&created_ats[gte]=${start_date}T00:00:00Z"
    echo "    [Limiting search to sandboxes active starting on ${start_date} (00:00:00)]"
fi

# If an end date was given, filter for sandboxes created before the very end of
# the day given and before.
if [ $end_date ]; then
    extra_params="${extra_params}&created_ats[lte]=${end_date}T23:59:59Z"
    echo "    [Limiting search to sandboxes active no later than ${end_date} (23:59:59)]"
fi

echo

# Get all of the sandbox orgs in a format to be used with a cf curl call.
echo "...Retrieving all sandbox org names..."
sandbox_org_names=$(cf orgs | \grep '^sandbox' | tr '\n' ',')

# Get all of the GUIDs for the sandbox orgs in a format to be used with a cf
# curl call.
echo "...Retrieving all sandbox org GUIDs..."
sandbox_org_guids=$(cf curl "/v3/organizations?names=${sandbox_org_names}&per_page=5000" | jq -r '.resources | map(.guid) | join(",")')

# Retrieve a count of all spaces across all sandbox orgs.
echo "...Retrieving total number of spaces for all sandbox orgs..."
total_sandbox_spaces=$(cf curl "/v3/spaces?organization_guids=${sandbox_org_guids}&per_page=5000" | jq -r '.pagination.total_results')

# If we've set any dates, also check for spaces created during that time period.
if [ $extra_params ]; then
    echo "...Retrieving number of spaces created in all sandbox orgs during dates given..."
    total_sandboxe_spaces_created=$(cf curl "/v3/spaces?organization_guids=${sandbox_org_guids}&per_page=5000${extra_params}" | jq -r '.pagination.total_results')
fi

# Retrieve the count of all running apps across all sandbox orgs, regardless of
# the actual space they're running in.
echo "...Retrieving total number of active sandboxes for all sandbox orgs..."
total_active_sandboxes=$(cf curl "/v3/apps?organization_guids=${sandbox_org_guids}&per_page=5000${extra_params}" | jq -r '.pagination.total_results')

# Print the final results.
echo
echo "Total number of sandbox spaces: ${total_sandbox_spaces}"
echo "Total number of active sandboxes: ${total_active_sandboxes}"

if [ $extra_params ]; then
    echo "Total number of sandbox spaces created during given dates: ${total_sandboxe_spaces_created}"
fi
