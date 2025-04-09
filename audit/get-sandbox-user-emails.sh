#!/bin/bash

# Get a list of all orgs names prepended with the word sandbox"
orgs=($(cf orgs | grep '^sandbox'))

echo "Username, Org GUID"

# Loop through the array and look up quota details.
for org in "${orgs[@]}"
do
    guid=$(cf org $org --guid)

    emails=($(cf curl "/v3/organizations/$guid/users" | jq '.resources | .[] | .username'))
    for email in "${emails[@]}"
    do
        echo "${email}, ${guid}"
    done
    sleep 1
done