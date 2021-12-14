#!/bin/bash

# Get number of pages of results
total_pages=$(cf curl "/v3/apps?per_page=1" | jq .pagination.total_pages)
echo "$total_pages total apps to look up"

# Put header row in CSV file
echo "\"name\",\"app_guid\",\"created_at\",\"updated_at\",\"buildpack\",\"state\",\"space_guid\",\"space_name\",\"org_guid\",\"org_name\"" > apps-listing.csv

# Query CF API and parse results, store in CSV
i=1
while [ "$i" -le "$total_pages" ]; do

    # Get the details for an app.
    app_json=$(cf curl "/v3/apps?per_page=1&page=$i")
    app_details=$(echo "$app_json" | jq -r '.resources[] | [.name, .guid, .created_at, .updated_at, .lifecycle.data.buildpacks[]? // "Docker", .state] | @csv')
    
    #Get the space GUID to look up the space name and org details.
    space_guid=$(echo "$app_json" | jq -r '.resources[].relationships.space.data.guid')
    spaces_json=$(cf curl /v3/spaces/"$space_guid")
    space_name=$(echo "$spaces_json" | jq -r '.name')
    
    # Get the org guid and use it to look up the org name.
    org_guid=$(echo "$spaces_json" | jq -r '.relationships.organization.data.guid')
    org_name=$(cf curl /v3/organizations/"$org_guid" | jq .name)

    # Store the details in CSV file
    app_details+=",$space_guid,$space_name,$org_guid,$org_name"
    echo "$app_details" >> apps-listing.csv

    # Echo out progress.
    echo "Finished app $i"

    # Rinse. Repeat.
    sleep 1
    i=$((i+1))

done


