#!/bin/bash

set -e

RED='\033[0;31m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
PURPLE='\033[0;35m'
NC='\033[0m'

if [[ -z $ci_env ]]
then
  echo -e "Please set a ${YELLOW}\$ci_env${NC} variable to continue from ${YELLOW}fly targets${NC}"
  echo -e "eg, ${PURPLE}ci_env=fr ./generate-all-certificates.sh --grab-cert${NC}"
  exit 99
fi

pipelines=$(
fly -t $ci_env pipelines | \
grep -Eo '^[a-z0-9\-]+'
)

for pipeline in $pipelines
do
  repo_list=$(
  fly -t $ci_env gp -p "$pipeline" | \
  grep -E 'uri.*github' | \
  grep -oE '\/[0-9a-zA-Z\-]+\/[A-Z0-9a-z\-]+(\.git)?' | \
  uniq | \
  awk '{ print tolower($0) }' | \
  sed -e "s/\.git//" | \
  sed -e "s/\n//"
  )
  echo "Found $( echo "${repo_list}" | wc -l ) repositories in ${pipeline}"
  echo "${repo_list}"
done
