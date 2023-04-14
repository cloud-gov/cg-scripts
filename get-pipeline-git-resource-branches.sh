#!/usr/bin/env bash

function usage {
  echo -e "
  ./$( basename "$0" ) repo-name [pipeline-name] [--help, -h]

  Get all git resources in Concourse pipelines that don\'t have commit signing
  configured

  Examples:
  # Find all uses of repo1 across all pipelines
  ./$( basename "$0" ) repo1

  # Find all uses of repo1 in a specific pipeline
  ./$( basename "$0" ) repo1 pipeline1

  # Find all uses of repo1 and repo2 across all pipelines
  ./$( basename "$0" ) \"repo1|repo2\"

  Optional environment variable \$CI_URL matching your Concourse URL.
  example: CI_URL=https://ci.fr.cloud.gov ./$( basename "$0" )

  \$CI_URL, Defaults to https://ci.fr.cloud.gov
  "
  exit
}

if [ -z "$1" ]; then
  echo "Repo name is required as first argument to script"
  usage
fi

while getopts ":h" opt; do
  case ${opt} in
    h )
        usage
        exit 0
        ;;
    * )
        usage
        exit 0
        ;;
  esac
done


CI_URL="${CI_URL:-"https://ci.fr.cloud.gov"}"
FLY_TARGET=$(fly targets | grep "${CI_URL}" | head -n 1 | awk '{print $1}')

if ! fly --target "${FLY_TARGET}" workers > /dev/null; then
  echo "Not logged in to concourse"
  exit 1
fi

function find_git_resources_for_branch {
  fly -t ci get-pipeline --pipeline "$2" --json \
    | jq --arg repo "$1" '.resources[] |
        select(.type=="git") |
        select(.source.uri | test("github.com.*(cloud-gov|18[Ff])")) |
        select(.source.uri | test($repo))'
}

function find_git_resource_uris {
  resource_names=$(find_git_resources_for_branch "$1" "$2" | jq '"repo: " + .source.uri + ", branch: " + .source.branch')
  if [[ $resource_names ]]; then
      printf 'pipeline: %s\n' "$2"
      echo "$resource_names"
      printf "\n"
  fi
}

if [ -z "$2" ]; then
  fly --target "${FLY_TARGET}" pipelines | tail -n +1 |  while read -r line; do
      pipeline_name=$(echo "$line"  | awk '{print $2}')
      
      find_git_resource_uris "$1" "$pipeline_name"
  done
else
  find_git_resource_uris "$1" "$2"
fi

