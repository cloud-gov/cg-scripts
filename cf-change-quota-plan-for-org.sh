#!/bin/bash

# Taken from https://docs.pivotal.io/pivotalcf/1-6/opsguide/change-quota-plan.html

set -e

if [ -z "$1" ]
then
  echo -e "\033[31m\$ORG_NAME not defined\033[0m"
  echo -e "usage: \033[32m./cf-change-quota-plan-for-org.sh \033[34m\$ORG_NAME\033[0m"
  exit 99
fi

if [ -z "$2" ]
then
  echo -e "\033[31m\$NEW_QUOTA_NAME not defined\033[0m"
  echo -e "usage: \033[32m./cf-change-quota-plan-for-org.sh \033[34m\$ORG_NAME\033[0m \033[34m\$NEW_QUOTA_NAME\033[0m"
  exit 99
fi

ORG_NAME=$1
NEW_QUOTA_NAME=$2
OLD_QUOTA_NAME=$(cf org "$ORG_NAME" | grep quota: | awk '{print $2}')

echo -ne "\033[36m$ORG_NAME\033[0m GUID: "
ORG_GUID=$(
  CF_TRACE=true cf org "$ORG_NAME" | \
  grep -B7 "$ORG_NAME" | \
  grep -A1 metadata | \
  grep guid | \
  awk '{gsub(/\"guid\":|\ |\"|\,/,"")}1'
)
echo -e "\033[34m$ORG_GUID\033[0m"

echo -ne "\033[36m$OLD_QUOTA_NAME\033[0m GUID: "
ORG_QUOTA_DEFINITION_GUID=$(
  cf curl "/v2/organizations/$ORG_GUID" -X 'GET' | \
  grep quota_definition_guid | \
  awk '{print $2}' | \
  sed -E 's/"|,//g'
)
echo -e "\033[34m$ORG_QUOTA_DEFINITION_GUID\033[0m"

echo -ne "\033[36m$NEW_QUOTA_NAME\033[0m GUID: "
NEW_QUOTA_GUID=$(
  CF_TRACE=true cf quota "$NEW_QUOTA_NAME" | \
  grep guid | \
  awk '{gsub(/\"guid\":|\ |\"|\,/,"")}1'
)
echo -e "\033[34m$NEW_QUOTA_GUID\033[0m"

# Step 0: Confirm the inputs.
# http://stackoverflow.com/a/226724/358804
printf "\n\nUpdate quota definition for \033[36m%s\033[0m from \033[33m%s\033[0m to \033[33m%s\033[0m ?\n\n" "$ORG_NAME" "$OLD_QUOTA_NAME" "$NEW_QUOTA_NAME"
select yn in "Yes" "No"; do
  case $yn in
    Yes ) break;;
    No ) exit 1;;
  esac
done


echo -e "Updating quota from \033[34m$OLD_QUOTA_NAME\033[0m to \033[34m$NEW_QUOTA_NAME\033[0m for \033[36m$ORG_NAME\033[0m"

cf curl "/v2/organizations/$ORG_GUID" \
        -X 'PUT' \
        -d "{\"quota_definition_guid\":\"$NEW_QUOTA_GUID\"}"
