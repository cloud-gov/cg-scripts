#!/bin/bash

CI_URL="${CI_URL:-"https://ci.fr.cloud.gov"}"
FLY_TARGET=$(fly targets | grep "${CI_URL}" | head -n 1 | awk '{print $1}')

if ! fly --target "${FLY_TARGET}" workers > /dev/null; then
  echo "Not logged in to concourse"
  exit 1
fi

pipelines=$(fly --target "$FLY_TARGET" pipelines | grep -Eo '^[a-z0-9\-]+')

echo "Checking pipelines for CF users"
echo "Total pipelines flown ${CI_URL}: $( echo "$pipelines" | wc -w )"

for pipeline in $pipelines
do
  match=$(
  fly --target "$FLY_TARGET" get-pipeline --pipeline "$pipeline" | \
  spruce json | \
  jq -e '.resources[] | select( .type == "cf" ) | .source'
  )
  if [ "$?" -eq 0 ]
  then
    echo
    echo "Found CF user in fly --target ${FLY_TARGET} get-pipeline --pipeline ${pipeline}"
    echo "  operator login commands: "
    echo "${match}" | jq -r '"    cf login --sso -a \(.api) -o \(.organization) -s \(.space)"'
    echo "  deployer login commands: "
    echo "${match}" | jq -r '"    cf login -a \(.api) -u \(.username) -p '\''\(.password)'\'' -o \(.organization) -s \(.space)"'
  fi
done
