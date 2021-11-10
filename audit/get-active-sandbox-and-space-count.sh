#!/bin/bash

# Counts the number of current active sandboxes in the platform.

# An active sandbox is defined as any user's sandbox space with 1 or more
# running apps in it.

# We can determine this by using the cf CLI and CAPI to retrieve all sandbox
# orgs, then filter a list of all apps with those corresponding org GUIDs.

echo "Getting total counts of active sandboxes and sandbox spaces..."
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

# Retrieve the count of all running apps across all sandbox orgs, regardless of
# the actual space they're running in.
echo "...Retrieving total number of active sandboxes for all sandbox orgs..."
total_active_sandboxes=$(cf curl "/v3/apps?organization_guids=${sandbox_org_guids}&per_page=5000" | jq -r '.pagination.total_results')

# Print the final results.
echo
echo "Total number of sandbox spaces: $total_sandbox_spaces"
echo "Total number of active sandboxes: $total_active_sandboxes"
