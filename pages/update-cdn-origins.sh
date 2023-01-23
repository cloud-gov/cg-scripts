#! /bin/bash

set -e

display_usage() {
  echo -e "\nUsage: $0 [max-rows] [offset]\n"
  echo -e "  max-rows: process at most this number of input rows (default: unlimited)\n"
  echo -e "  offset:   skip an initial set of input rows (default: 0)\n"
}

if [[ ( $@ == "--help") ||  $@ == "-h" ]]
then
  display_usage
  exit 0
fi

# CF Auth
cf api "${CF_API_URL}"
(set +x; cf auth "${CF_USERNAME}" "${CF_PASSWORD}")

cf target -o "${CF_ORG}"


max_rows=${1:--1}

offset=${2:-0}

# Waiting for service instance to finish being processed.
wait_for_service_instance() {
  local service_name=$1
  local guid=$(cf service --guid $service_name)
  local status=$(cf curl /v2/service_instances/${guid} | jq -r '.entity.last_operation.state')

  while [ "$status" == "in progress" ]; do
    sleep 60
    status=$(cf curl /v2/service_instances/${guid} | jq -r '.entity.last_operation.state')
  done
}

rows_processed=0
query="select \"serviceName\",origin from domain where state='provisioned';"
domains=`psql ${DB_URI} --csv -t -c "$query"`
while IFS="," read -r service_instance current_origin
do
  if [[ $offset -gt 0 ]]
  then
    ((offset--))
    continue
  fi

  ((rows_processed++))

  if [[ ($max_rows -gt 0) && ($rows_processed -gt $max_rows)]]
  then
    break
  fi

  if [[ $current_origin =~ (.*)\.app\.cloud\.gov$ ]]
  then
    bucket=${BASH_REMATCH[1]}
    new_origin="$bucket.sites.pages.cloud.gov"

    # For the moment, outputting instead of executing this command...
    echo "cf update-service $service_instance -c '{\"origin\": \"$new_origin\"}'"

    # wait_for_service_instance $SERVICE_INSTANCE"
    echo "wait_for_service_instance $SERVICE_INSTANCE"

    update="update domain set origin='$new_origin' where \"serviceName\"='$service_instance';"
    # psql ${DB_URI} -c "$update"`
    echo "psql DB_URI -c \"$update\""
    echo
  fi
done <<< $domains
