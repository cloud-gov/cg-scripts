#!/usr/bin/env bash

# list all our repos
# note that this requires the github cli tool
usage() {
    echo "usage: $0 [-i]" 1>&2
    echo "list all cloud-gov repos" 1>&2
    echo "use -i to exclude forks" 1>&2
    exit 1
}

api_qs=""
while getopts ":i" opt; do
  case $opt in
    i)
      api_qs="?type=member"
      ;;
    \?)
      usage
      ;;
  esac
done

gh api --paginate /orgs/cloud-gov/repos${api_qs}
