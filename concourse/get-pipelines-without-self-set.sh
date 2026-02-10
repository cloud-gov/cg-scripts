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

function get_number_of_self_set_tasks {
  fly -t "${FLY_TARGET}" get-pipeline --pipeline "$1" --json \
    | jq '[.jobs[].plan[] | has("set_pipeline")] | map(select(.)) | length'
}

function report_pipelines_without_self_set {
  length=$(get_number_of_self_set_tasks "$1")
  if [[ $length != "1" ]]; then
      printf 'pipeline: %s\n' "$1"
  fi
}

if [ -z "$1" ]; then
  fly --target "${FLY_TARGET}" pipelines | tail -n +1 |  while read -r line; do
      pipeline_name=$(echo "$line"  | awk '{print $2}')

      report_pipelines_without_self_set "$pipeline_name"
  done
else
  report_pipelines_without_self_set "$1"
fi

