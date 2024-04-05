#!/bin/bash

set -e
set -u

if [ "$#" -ne 5 ]; then
  echo
  echo "Usage:"
  echo "   ./create-concourse-team.sh <concourse target> <team name> <client id> <client secret> <required scope>"
  echo
  echo "   EX:  ./create-concourse-team.sh govcloud main concourse_client F00b4r concourse.main"
  echo
    exit 1
fi

TARGET=$1
TEAM=$2
CLIENT_ID=$3
CLIENT_SECRET=$4
SCOPE=$5

fly -t $TARGET set-team -n $TEAM \
    --generic-oauth-display-name "UAA" \
    --generic-oauth-client-id $CLIENT_ID \
    --generic-oauth-client-secret $CLIENT_SECRET \
    --generic-oauth-auth-url https://opslogin.fr.cloud.gov/oauth/authorize \
    --generic-oauth-token-url https://opsuaa.fr.cloud.gov/oauth/token \
    --generic-oauth-scope $SCOPE \
    --generic-oauth-auth-url-param scope:$SCOPE
