#!/usr/bin/env bash

if [ "$#" -ne 1 ]; then
  echo
  echo "Usage:"
  echo "   ./cf-get-org-apps.sh <organization-guid>"
  echo

  exit 1
fi

# todo: handle pagination for multiple pages of spaces
spaces=$(cf curl "/v3/spaces?organization_guids=${1}" | jq -r '.resources[] | .name + " " + .guid')
output=""

while IFS= read -r space_line; do
    read -ra space_data <<< "$space_line"
    space_guid=${space_data[1]}

    # todo: handle pagination for multiple pages of apps
    apps=$(cf curl "/v3/apps?organization_guids=${1}&space_guids=${space_guid}")
    apps_data=$(echo "$apps" | jq -r '.resources[] | select(.state == "STARTED") | .name + " " + .guid + " "')

    while IFS= read -r app_line; do
        read -ra app_data <<< "$app_line"

        mem_info="$(cf curl "/v3/apps/${app_data[1]}/processes" | jq -r '.resources[] | (.instances | tostring) + "," + (.memory_in_mb | tostring)')"
        output_line="${space_data[0]},${app_data[0]},$mem_info"
        output="${output}$output_line "
    done <<< "$apps_data"
done <<< "$spaces"

headers="space,app_name,instances,memory_in_mb"
separators="-----,--------,---------,------------"
echo "$headers $separators $output" | tr " " "\n" | column -t -s ","
