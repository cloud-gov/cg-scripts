#!/bin/bash

set -eu

RED='\033[0;31m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
PURPLE='\033[0;35m'
NC='\033[0m'

if [[ -z $CG_PIPELINE ]]
then
  echo -e "${RED}ERROR${NC} Please set a ${YELLOW}\$CG_PIPELINE${NC} variable pointing to a clone of ${YELLOW}https://github.com/18F/cg-pipeline-tasks${NC}"
  echo -e "eg, ${PURPLE}CG_PIPELINE=~/dev/cg-pipeline-tasks ./generate-concourse-environment.sh"
  exit 98
fi

if [[ -z $SECRETS_BUCKET ]]
then
  echo -e "${RED}ERROR${NC} Please set a ${YELLOW}\$SECRETS_BUCKET${NC} with the name of the ${YELLOW}s3 bucket where secrets are stored${NC}"
  echo -e "eg, ${PURPLE}SECRETS_BUCKET=my-aws-bucket ./generate-concourse-environment.sh"
  exit 98
fi

if [[ -z $CI_ENV ]]
then
  echo -e "${RED}ERROR${NC} Please set a ${YELLOW}\$CI_ENV${NC} with the name of the ${YELLOW}concourse target where the secret-rotationpipeline is stored${NC}"
  echo -e "eg, ${PURPLE}CG_PIPELINE=~/dev/cg-pipeline-tasks ./generate-concourse-environment.sh"
  exit 98
fi

# create a combined secrets file
echo "bogus_key: bogus" > secrets-combined.yml

# get environment secrets files
for ENVIRONMENT in $(echo ${ENVIRONMENTS:-"common master tooling development staging production"}); do

  # download from s3
  aws s3 cp s3://"${SECRETS_BUCKET}"/secrets-"${ENVIRONMENT}".yml secrets-"${ENVIRONMENT}".yml

  # tag secrets per environment
  spruce json secrets-${ENVIRONMENT}.yml \
    | jq --arg SOURCE "${ENVIRONMENT}_" '.secrets | with_entries(.key |= $SOURCE + .)' \
    | spruce merge \
    > secrets-${ENVIRONMENT}-updated.yml

  # merge into combined secrets
  spruce merge \
    --prune bogus_key \
    secrets-${ENVIRONMENT}-updated.yml \
    secrets-combined.yml \
    > tmp.yml
  mv tmp.yml secrets-combined.yml

  # remove temporary files
  rm -f secrets-${ENVIRONMENT}*yml

done

# merge environment secrets files & other concourse vars
if [ $# -gt 0 ]
then
  spruce merge \
    secrets-combined.yml \
    "$@" \
    > concourse-environment.yml
  echo "added vars from $@"
  rm secrets-combined.yml
else
  mv secrets-combined.yml concourse-environment.yml
fi

echo "output concourse-environment.yml"

