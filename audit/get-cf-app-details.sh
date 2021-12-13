#!/bin/bash

# Get number of pages of results
total_pages=$(cf curl "/v3/apps?per_page=1" | jq .pagination.total_pages)
echo "$total_pages total apps to look up"

# Put header row in CSV file
echo "\"name\",\"guid\",\"created_at\",\"updated_at\",\"buildpack\",\"state\",\"org_guid\",\"org_name\"" > apps-listing.csv

# Query CF API and parse results, store in CSV
i=1
while [ "$i" -le "$total_pages" ]; do

    # Get the details for an app.
    app_json=$(cf curl "/v3/apps?per_page=1&page=$i")
    details=$(echo "$app_json" | jq -r '.resources[] | [.name, .guid, .created_at, .updated_at, .lifecycle.data.buildpacks[]? // "Docker", .state] | @csv')
    
    #Get the space GUID to look up the org details.
    space_guid=$(echo "$app_json" | jq -r '.resources[].relationships.space.data.guid')
    org_guid=$(cf curl /v3/spaces/"$space_guid" | jq -r '.relationships.organization.data.guid')
    
    # Use the org GUID to look up the app name.
    org_name=$(cf curl /v3/organizations/"$org_guid" | jq .name)

    # Store the details in CSV file
    details+=",$org_guid, $org_name"
    echo "$details" >> apps-listing.csv

    # Echo out progress.
    echo "Finished app $i"

    # Rinse. Repeat.
    sleep 1
    i=$((i+1))
    
done


