#!/usr/bin/env bash

# set -x

if [ "$#" -ne 1 ]; then
  echo
  echo "Usage:"
  echo "   ./cf-get-org-apps.sh <organization-name>"
  echo

  exit 1
fi

results_per_page=50
org_guid=$(cf org "$1" --guid)
output=""

function get_org_spaces {
  page=1
  echo $1

  while true
  do
    results=$(cf curl "/v3/spaces?organization_guids=${1}&per_page=${results_per_page}&page=${page}")
    echo "$results" | jq -r '.resources[] | .name + " " + .guid'
    next=$(echo "$results" | jq -r '.pagination.next // empty')
    if [ -z "$next" ]; then
      break
    fi
    page=$((page + 1))
  done
}

function get_org_space_apps {
  page=1

  while true
  do
    results=$(cf curl "/v3/apps?organization_guids=${1}&space_guids=${2}&per_page=${results_per_page}&page=${page}")
    echo "$results" | jq -r '.resources[] | .name + " " + .guid'
    next=$(echo "$results" | jq -r '.pagination.next // empty')
    if [ -z "$next" ]; then
      break
    fi
    page=$((page + 1))
  done
}

while IFS= read -r space_line; do
  if [ -z "$space_line" ]; then
    break
  fi
  
  read -ra space_data <<< "$space_line"
  space_guid=${space_data[1]}
  
  while IFS= read -r app_line; do
    if [ -z "$app_line" ]; then
      break
    fi

    read -ra app_data <<< "$app_line"
    mem_info="$(cf curl "/v3/apps/${app_data[1]}/processes" | jq -r '.resources[] | (.instances | tostring) + "," + (.memory_in_mb | tostring)')"
    output_line="${space_data[0]},${app_data[0]},$mem_info"
    output="${output}$output_line "
  done <<< "$(get_org_space_apps "$org_guid" "$space_guid")"
done <<< "$(get_org_spaces "$org_guid")"

if [ "$output" != "" ]; then
  headers="space,app_name,instances,memory_in_mb"
  separators="-----,--------,---------,------------"
  echo "$headers $separators $output" | tr " " "\n" | column -t -s ","
fi
