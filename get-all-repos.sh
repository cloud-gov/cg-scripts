#!/bin/bash

set -e

RED='\033[0;31m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
PURPLE='\033[0;35m'
NC='\033[0m'

if [[ -n $1 && $1 =~ (-h|--help)$ ]]
then
  echo -e "
  ./get-all-repos [--help, -h] [--verbose, -v]

  Get all unique GitHub respositories referenced by pipelines on a Concourse server.
  
  Requires an environment variable ${YELLOW}\$ci_env${NC} set matching ${YELLOW}\`fly targets\`${NC}
  eg, ${PURPLE}ci_env=fr ./get-all-repos --verbose${NC}
  "
  exit
fi

if [[ -z $ci_env ]]
then
  echo -e "Please set a ${YELLOW}\$ci_env${NC} variable to continue from ${YELLOW}\`fly targets\`${NC}"
  echo -e "eg, ${PURPLE}ci_env=fr ./get-all-repos${NC}"
  exit 99
fi

repo_list=$( mktemp )

pipelines=$(
fly -t $ci_env pipelines | \
grep -Eo '^[a-z0-9\-]+'
)

for pipeline in $pipelines
do
  pipeline_repo_list=$(
  fly -t $ci_env gp -p "$pipeline" | \
  grep -E 'uri.*github' | \
  grep -oE '\/[0-9a-zA-Z\-]+\/[A-Z0-9a-z\-]+(\.git)?' | \
  uniq | \
  awk '{ print tolower($0) }' | \
  sed -e "s/\.git//" | \
  sed -e "s/\n//"
  )

  if [[ -n $1 && $1 =~ (-v|--verbose)$ ]]
  then
    echo -e "${GREEN}Found${NC} $( echo "${pipeline_repo_list}" | wc -l ) repositories in ${YELLOW}${pipeline}${NC}"
    echo -e "${pipeline_repo_list}\n-----"
  fi
  
  echo "${pipeline_repo_list}" >> $repo_list
done

cat $repo_list | sort -u
rm $repo_list
