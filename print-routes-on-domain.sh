#!/bin/bash

set -e

if [ -z $1 ]; then
        echo "Feed it a domain name and this script prints information about "
        echo "the routes using that domain. Information is printed in CSV "
        echo "format including: route, org name, space name, space developers."
        echo " "
	echo "Usage: "
        echo "  $0 <DOMAIN_NAME>"
        echo " "
        exit 1
fi 

domain_name=$1

domain_guid=$(cf curl "/v3/domains?names=${domain_name}" | jq -r '.resources[].guid')

route_guids=$(cf curl "/v3/routes?domain_guids=${domain_guid}&per_page=5000" | jq -r '.resources[] | .guid')

for route_guid in $route_guids; do
        
        # get the host, space_guid
        route_json=$(cf curl "/v3/routes/${route_guid}")
        route=$(echo "$route_json" | jq -r '.url')
        space_guid=$(echo "$route_json" | jq -r '.relationships.space.data.guid')
        
        # get the space name, org guid
        space_json=$(cf curl "/v3/spaces/${space_guid}")
        space_name=$(echo "$space_json" | jq -r '.name')
        org_guid=$(echo "$space_json" | jq -r '.relationships.organization.data.guid')

        space_developers=""
        # get the space developers
        space_dev_guids=$(cf curl "/v3/roles?space_guids=${space_guid}" | jq -r '.resources[] | select(.type == "space_developer") | .relationships.user.data.guid')
        for space_dev_guid in $space_dev_guids; do
                space_developer=$(cf curl "/v3/users/${space_dev_guid}" | jq -r '.presentation_name')
                space_developers="${space_developers} ${space_developer}"
        done

        # get the org name
        org_name=$(cf curl "/v3/organizations/${org_guid}" | jq -r '.name')

        echo "${route}, ${org_name}, ${space_name}, ${space_developers}"
done