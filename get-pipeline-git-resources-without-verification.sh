#!/usr/bin/env bash

if [[ -n $1 && $1 =~ (-h|--help)$ ]]
then
  echo -e "
  ./$( basename "$0" ) [--help, -h]

  Get all git resources in Concourse pipelines that don\'t have commit signing
  configured

  Optional environment variable \$CI_URL matching your Concourse URL.
  eg, CI_URL=https://ci.fr.cloud.gov ./$( basename "$0" )

  \$CI_URL, Defaults to https://ci.fr.cloud.gov
  "
  exit
fi

CI_URL="${CI_URL:-"https://ci.fr.cloud.gov"}"
FLY_TARGET=$(fly targets | grep "${CI_URL}" | head -n 1 | awk '{print $1}')

if ! fly --target "${FLY_TARGET}" workers > /dev/null; then
  echo "Not logged in to concourse"
  exit 1
fi

function get_unconfigured_git_resources {
   fly -t ci get-pipeline --pipeline "$1" --json \
        | jq '.resources[] |
            select(.type=="git") |
            select(.source.uri | test("github.com.*(cloud-gov|18[Ff])")) |
            select(.source | has("commit_verification_keys") | not) |
            .name'
}

fly --target "${FLY_TARGET}" pipelines | tail -n +1 |  while read -r line; do
    pipeline_name=$(echo "$line"  | awk '{print $2}')
    
    output=$(get_unconfigured_git_resources "$pipeline_name")
    if [[ $output ]]; then
        printf 'pipeline: %s\n' "$pipeline_name"
        echo "$output"
        printf "\n"
    fi
done