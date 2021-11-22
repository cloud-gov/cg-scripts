#!/usr/bin/env bash

usage() {
    echo "usage: $0 [-i]" 1>&2
    echo "clone all cloud-gov repos into your current working directory" 1>&2
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

repos=$(gh api --paginate /orgs/cloud-gov/repos${api_qs} -q '.[].ssh_url')
for repo in ${repos}; do
    git clone $repo
done
