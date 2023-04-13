#!/usr/bin/env bash

function usage {
  echo -e "
  ./$( basename "$0" ) [pipeline-name] [--help, -h]

  Get all git resources in Concourse pipelines that don\'t have commit signing
  configured

  Optional environment variable \$CI_URL matching your Concourse URL.
  example: CI_URL=https://ci.fr.cloud.gov ./$( basename "$0" )

  Optional argument for specific pipeline to check
  example: ./$( basename "$0" ) pipeline-name

  \$CI_URL, Defaults to https://ci.fr.cloud.gov
  "
  exit
}

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

function find_git_resources_without_commit_verification {
  fly -t ci get-pipeline --pipeline "$1" --json \
    | jq '.resources[] |
        select(.type=="git") |
        select(.source.uri | test("github.com.*(cloud-gov|18[Ff])")) |
        select(.source.branch=="master")'
}

function report_git_resources_without_verification {
  resource_names=$(find_git_resources_without_commit_verification "$1" | jq .name)
  if [[ $resource_names ]]; then
      printf 'pipeline: %s\n' "$1"
      echo "$resource_names"
      printf "\n"
  fi
}

if [ -z "$1" ]; then
  fly --target "${FLY_TARGET}" pipelines | tail -n +1 |  while read -r line; do
      pipeline_name=$(echo "$line"  | awk '{print $2}')
      
      report_git_resources_without_verification "$pipeline_name"
  done
else
  report_git_resources_without_verification "$1"
fi

