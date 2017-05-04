#!/bin/bash

set -e

YELLOW='\033[0;33m'
PURPLE='\033[0;35m'
NC='\033[0m'

if [[ -z $ci_env ]]
then
  echo -e "Please set a ${YELLOW}\$ci_env${NC} variable to continue from \
${YELLOW}fly targets${NC}"
  echo -e "eg, ${PURPLE}ci_env=fr ./generate-all-certificates.sh \
--grab-cert${NC}"
  exit 99
fi

pipelines=$(
fly -t "$ci_env" pipelines | \
grep -Eo '^[a-z0-9\-]+'
)

repositories=$(
for pipeline in $pipelines
do
  fly -t "$ci_env" gp -p "$pipeline" | \
  grep -E 'uri.*github' | \
  grep -oE '\/[0-9a-zA-Z\-]+\/[A-Z0-9a-z\-]+(\.git)?' | \
  uniq | \
  awk '{ print tolower($0) }' | \
  sed -e "s/\.git//" | \
  sed -e "s/\n//"
done
)

repositories=$(echo "${repositories}" | tr " " "\n" | sort | uniq)
our_repo=''
not_repo=''

for repo in $repositories
do
  if [[ $repo =~ ^\/18f\/ ]] ; then
    our_repo="${our_repo}${repo} "
  else
    not_repo="${not_repo}${repo} "
  fi
done

our_repo="${our_repo%"${our_repo##*[![:space:]]}"}"
not_repo="${not_repo%"${not_repo##*[![:space:]]}"}"

echo "-----------------------------"
echo "GitHub Repositories Under 18F"
echo "-----------------------------"
echo "${our_repo}" | tr " " "\n"
echo "---------------------------------"
echo "GitHub Repositories NOT Under 18F"
echo "---------------------------------"
echo "${not_repo}" | tr " " "\n"
