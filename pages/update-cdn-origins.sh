#! /bin/bash

set -e

# Process parameters
display_usage() {
  echo -e "\nUsage: $0 [max-domains]\n"
  echo -e "  max-domains: process at most this number of input rows (default: unlimited)\n"
}

if [[ ( $@ == "--help") ||  $@ == "-h" ]]
then
  display_usage
  exit 0
fi

max_domains=${1:--1}

# Check for required environment variables
[ -z "${CF_API_URI}"  ] && { echo -e "\n Required CF_API_URI environment variable is not set\n";  exit 1; }
[ -z "${CF_USERNAME}" ] && { echo -e "\n Required CF_USERNAME environment variable is not set\n"; exit 1; }
[ -z "${CF_PASSWORD}" ] && { echo -e "\n Required CF_PASSWORD environment variable is not set\n"; exit 1; }
[ -z "${CF_ORG}"      ] && { echo -e "\n Required CF_ORG environment variable is not set\n"; exit 1; }
[ -z "${CF_SPACE}"    ] && { echo -e "\n Required CF_SPACE environment variable is not set\n"; exit 1; }
[ -z "${DB_URI}"      ] && { echo -e "\n Required DB_URI environment variable is not set\n"; exit 1; }

# Authenticate and set Cloud Foundry target
cf api "${CF_API_URI}"
(set +x; cf auth "${CF_USERNAME}" "${CF_PASSWORD}")
cf target -o "${CF_ORG}" -s "${CF_SPACE}"

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

# Find domains that need to be updated and iterate through them
domains_processed=0
query="select id,\"serviceName\",origin from domain where state='provisioned' and origin like '%app.cloud.gov';"
domains=`psql ${DB_URI} --csv -t -c "$query"`
while IFS="," read -r id service_instance current_origin
do
  let "domains_processed=$domains_processed + 1"

  if [[ ($max_domains -gt 0) && ($domains_processed -gt $max_domains)]]
  then
    break
  fi

  # Make sure the domain origin is of the old form
  if [[ $current_origin =~ (.*)\.app\.cloud\.gov$ ]]
  then
    bucket=${BASH_REMATCH[1]}
    new_origin="$bucket.sites.pages.cloud.gov"

    # Update the service
    echo "Updating $service_instance origin"
    cf update-service $service_instance -c '{"origin": "'$new_origin'"}'

    # Wait for update-service process to complete"
    echo "... waiting ..."
    wait_for_service_instance $service_instance
    echo "Service instance updated."

    # Update domain in core DB
    echo "Updating domain table."
    update="update domain set origin='$new_origin' where \"id\"='$id';"
    psql ${DB_URI} -c "$update"
    echo
  fi

done <<< $domains

echo "Done. Processed domains: $domains_processed"
