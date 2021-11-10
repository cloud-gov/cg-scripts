#!/bin/bash

# Get a count of all spaces and sandboxes and the sandbox orgs.

# This is done by retrieving a list of all orgs that are prefixed with
# "sandbox-" and then counting the number of apps in each space within the org.
# If there is more than 1 app, we know the space is active and therefore the
# sandbox is being used by that user, so we can count that as an active sandbox.

sandbox_orgs=$(cf orgs | \grep '^sandbox')
total_spaces=0
total_active_sandboxes=0

# Loop through the array of sandbox orgs to retrieve each org's GUID and all of
# space GUIDs that exist underneath it.
# We also count the total number of spaces to get a running tally of total
# sandboxes, regardless of whether or not they're active.
for sandbox_org in "${sandbox_orgs[@]}"
do
    sandbox_org_guid=$(cf org $sandbox_org --guid)
    space_info=$(cf curl "/v3/spaces/?organization_guids=$sandbox_org_guid&per_page=5000")
    num_spaces=$(echo -n "${space_info}" | jq -r '.pagination.total_results')
    space_guids=$(echo -n "${space_info}" | jq -r '.resources | map(.guid) | join(",")')

    echo "Getting count of spaces and active sandboxes for $sandbox_org ($sandbox_org_guid)..."

    # Retrieve all of the running apps across all spaces in the sandbox org.
    num_apps=$(cf curl "/v3/apps?organization_guids=$sandbox_org_guid&space_guids=$space_guid&per_page=5000" | jq -r '.pagination.total_results')

    total_active_sandboxes=$((total_active_sandboxes + num_apps))
    total_spaces=$((total_spaces + num_spaces))

    echo "  ...Found $num_apps active sandboxes; $total_active_sandboxes active sandboxes total so far."
    echo "  ...Found $num_spaces spaces; $total_spaces spaces total so far."
    echo
    sleep 1
done

# Print final output
echo
echo "Total Number of spaces within sandbox orgs: $total_spaces"
echo "Total Number of active sandboxes: $total_active_sandboxes"
