#!/usr/bin/env bash

CI_URL="${CI_URL:-"https://ci.fr.cloud.gov"}"
FLY_TARGET=$(fly targets | grep "${CI_URL}" | head -n 1 | awk '{print $1}')
# REPO_REGEX='github.com.*\(cloud-gov\|18[fF]\)'

if ! fly --target "${FLY_TARGET}" workers > /dev/null; then
  echo "Not logged in to concourse"
  exit 1
fi

fly --target "${FLY_TARGET}" pipelines | tail -n +1 |  while read -r line; do
    # echo "$line"
    # my_process "$line"
    pipeline_name=$(echo "$line"  | awk '{print $2}')
    echo $pipeline_name
done