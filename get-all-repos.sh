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
   ./$( basename "$0" ) [--help, -h]
 
   Get all unique GitHub respositories referenced by pipelines on a Concourse server.
   
   Requires an environment variable ${YELLOW}\$ci_env${NC} set matching ${YELLOW}\`fly targets\`${NC}
   eg, ${PURPLE}ci_env=fr ./$( basename "$0" ) --verbose${NC}
   "
   exit
 fi

if [[ -z $ci_env ]]
then
  echo -e "Please set a ${YELLOW}\$ci_env${NC} variable to continue from \
${YELLOW}fly targets${NC}"
  echo -e "eg, ${PURPLE}ci_env=fr ./$( basename "$0" ) \
--grab-cert${NC}"
  exit 99
fi

echo -e "${CYAN}Targeting${NC} Concourse CI ${PURPLE}fly -t ${ci_env}${NC}"
echo -n

declare -a pipelines=($(
fly -t "$ci_env" pipelines | \
grep -Eo '^[a-z0-9\-]+'
))

num_pipelines="${#pipelines[@]}"
echo -e "${GREEN}Found${NC} ${num_pipelines} pipelines"

declare -a repositories=()
for pipeline in "${pipelines[@]}"
do
  # Needs extra whitespace in order to override the previous line completely.
  echo -ne "Processing ${YELLOW}$((num_pipelines--))${NC} ${pipeline}                                                        \r"
  repositories+=($(
    fly -t "$ci_env" gp -p "$pipeline" | \
    grep -E 'uri.*github' | \
    grep -oE '\/[0-9a-zA-Z\-]+\/[A-Z0-9a-z\-]+(\.git)?' | \
    uniq | \
    awk '{ print tolower($0) }' | \
    sed -e "s/\.git//" | \
    sed -e "s/\n//"
  ))
done

repositories=($(echo "${repositories[@]}" | tr " " "\n" | sort | uniq))
our_repo=''
not_repo=''

# Backspacing over the previous output to clear the progress line.
echo -ne "\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b                      "
echo
echo -e "${GREEN}Found${NC} ${#repositories[@]} repositories"

for repo in "${repositories[@]}"
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
echo -e "${GREEN}${our_repo}${NC}" | tr " " "\n"
echo "---------------------------------"
echo -e "GitHub Repositories ${RED}NOT${NC} Under 18F"
echo "---------------------------------"
echo -e "${YELLOW}${not_repo}${NC}" | tr " " "\n"
