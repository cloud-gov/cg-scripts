#!/usr/bin/env bash

function usage {
  echo -e "
  ./$( basename "$0" ) [pipeline-name] [--help, -h]

  Get definitions for Concourse pipeline(s)

  Downloads configuration YAML files for Concourse pipeline(s)

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

function get_pipeline {
  printf "\npipeline: %s\n\n" "$1" >&2
  fly --target "${FLY_TARGET}" get-pipeline -p "$1" > "$1.yml"
}

if [ -z "$1" ]; then
  for pipeline_name in $(fly --target "${FLY_TARGET}" pipelines | tail -n +1 | awk '{print $2}');
  do
    get_pipeline "$pipeline_name"
  done
else
  get_pipeline "$1"
fi

