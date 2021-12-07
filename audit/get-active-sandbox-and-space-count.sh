#!/bin/bash

set -e

# Provides counts for the following:
# - The total number of sandbox spaces currently in the platform
# - The number of current active sandboxes in the platform
# - Optionally provides the number of sandbox spaces created within a certain
#   timeframe given any provided dates or date range

# An active sandbox is defined as any user's sandbox space with 1 or more
# running apps in it.  Sandboxes are cleared out every 90 days from the time of
# first activity, so we can only ever count what is currently running.  That
# said, we can determine these counts by using the cf CLI and CAPI to retrieve
# all sandbox orgs, then filter a list of all apps with those corresponding org
# GUIDs.

# Sandbox spaces are defined as any space within a sandbox organization, e.g.,
# all spaces under the sandbox-gsa org.

# Help information for this script.
script_help() {
    cat << EOF

A script that provides counts for the following:

- The total number of sandbox spaces currently in the platform

- The number of current active sandboxes in the platform

- Optionally provides the number of sandbox spaces created within a certain
  timeframe given any provided dates or date range


Usage: ${0##*/} [--start-date START_DATE] [--end-date END_DATE]

    -?, -h, --help  Display this help message and exit

    --start-date    Retrieve an additional count of sandbox spaces that were
                    created at or after the provided start date; must be in
                    YYYY-MM-DD format

    --end-date      Retrieve an additional count of sandbox spaces that were
                    created at or before the provided end date; must be in
                    YYYY-MM-DD format

Including both the --start-date and --end-date arguments will restrict the
additional sandbox space count to the date range provided with both dates.
EOF
}

# Initialize sript variables.
start_date=""
end_date=""
extra_params=""

# Loop through script options to parse any provided options and retrieve their
# arguments.
while :; do
    case $1 in
        # Display script help.
        -\?|-h|--help)
            script_help
            exit
            ;;
        # Parse the start date option.
        --start-date)
            if [ "$2" ]; then
                if [[ "$2" =~ ^[0-9]{4}\-[0-9]{2}\-[0-9]{2}$ ]]; then
                    start_date=$2
                    shift
                else
                    echo 'ERROR: "--start-date" must be in YYYY-MM-DD format.'
                    exit
                fi
            else
                echo 'ERROR: "--start-date" requires a non-empty option argument.'
                exit
            fi
            ;;
        # Parse the end date option.
        --end-date)
            if [ "$2" ]; then
                if [[ "$2" =~ ^[0-9]{4}\-[0-9]{2}\-[0-9]{2}$ ]]; then
                    end_date=$2
                    shift
                else
                    echo 'ERROR: "--end-date" must be in YYYY-MM-DD format.'
                    exit
                fi
            else
                echo 'ERROR: "--end-date" requires a non-empty option argument.'
                exit
            fi
            ;;
        # Default case; ignore anything else passed in, there are no more
        # options to parse.
        *)
            break
    esac

    shift
done

echo "Getting total counts of active sandboxes and sandbox spaces..."

# If a start date was given, filter for sandbox spaces created at the start
# date and after, starting at the very beginning of the day.
if [ $start_date ]; then
    extra_params="${extra_params}&created_ats[gte]=${start_date}T00:00:00Z"
    echo "    [Perfoming extra search for sandbox spaces only created on ${start_date} (00:00:00) and after]"
fi

# If an end date was given, filter for sandbox spaces created before the very
# end of the day given and before.
if [ $end_date ]; then
    extra_params="${extra_params}&created_ats[lte]=${end_date}T23:59:59Z"
    echo "    [Perfoming extra search for sandbox spaces only created on ${end_date} (23:59:59) and before]"
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

# If we're given any dates, also check for spaces created during the specified
# timeframe(s).
if [ $extra_params ]; then
    echo "...Retrieving number of spaces created in all sandbox orgs during dates given..."
    total_sandboxe_spaces_created=$(cf curl "/v3/spaces?organization_guids=${sandbox_org_guids}&per_page=5000${extra_params}" | jq -r '.pagination.total_results')
fi

# Retrieve the count of all running apps across all sandbox orgs, regardless of
# the actual space they're running in.
echo "...Retrieving total number of current active sandboxes for all sandbox orgs..."
total_active_sandboxes=$(cf curl "/v3/apps?organization_guids=${sandbox_org_guids}&per_page=5000" | jq -r '.pagination.total_results')

# Print the final results.
echo
echo "Total number of sandbox spaces: ${total_sandbox_spaces}"
echo "Total number of current active sandboxes: ${total_active_sandboxes}"

# If any dates were given, provide the number of sandbox spaces created during
# the specific timeframe(s).
if [ $extra_params ]; then
    echo "Total number of sandbox spaces created during the given dates: ${total_sandboxe_spaces_created}"
fi
