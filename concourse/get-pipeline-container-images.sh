#!/usr/bin/env bash

function usage {
  echo -e "
  ./$( basename "$0" ) [pipeline-name] [--help, -h]

  Get all container images used in Concourse pipelines

  Generates a csv file listing all container images currently used

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

function find_resource_type_docker_images {
  echo "$1" | jq -r 'select(has("resource_types")) | [.resource_types[] |
        select(.type=="docker-image" or .type=="registry-image") |
        .source |
        .repository + (if .tag != null then ":" + (.tag|tostring) else "" end)] | unique'
}

function find_resource_docker_images {
  echo "$1" | jq -r '[.resources[] |
        select(.type=="docker-image" or .type=="registry-image") |
        .source |
        .repository + (if .tag != null then ":" + (.tag|tostring) else "" end)] | unique'
}

function find_task_docker_images {
  echo "$1" \
    | jq -r '[.jobs[].plan[] |
        select(.config | has("image_resource")) |
        select(.config.image_resource.type=="docker-image" or .config.image_resource.type=="registry-image") |
        .config.image_resource.source |
        .repository + (if .tag != null then ":" + (.tag|tostring) else "" end)] | unique'
}

function find_docker_images {
  printf "\npipeline: %s\n\n" "$1" >&2
  pipeline_json=$(fly -t ${FLY_TARGET}  get-pipeline --pipeline "$1" --json)
  resource_type_images=$(find_resource_type_docker_images "$pipeline_json")
  resource_images=$(find_resource_docker_images "$pipeline_json")
  task_images=$(find_task_docker_images "$pipeline_json")
  echo -e "$resource_type_images\n$resource_images\n$task_images" | jq -s 'add | unique | sort'
}

if [ -z "$1" ]; then
  all_images=""
  for pipeline_name in $(fly --target "${FLY_TARGET}" pipelines | tail -n +1 | awk '{print $2}');
  do
    images=$(find_docker_images "$pipeline_name")
    echo "$images" >&2

    all_images="$all_images\n$images"
  done

  printf "\nALL IMAGES\n\n"
  echo -e "$all_images" | jq -s 'add | unique | sort'
  echo -e "$all_images" | jq -rs 'add | unique | sort | .[]' > concourse_images.csv
else
  find_docker_images "$1"
fi

