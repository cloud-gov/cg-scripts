#!/bin/sh

set -e

if [ "$#" -ne 3 ]; then
  echo "\nUsage:\n\t./uaa-create-auth-client.sh <client name> <client secret> <callback url>"
  exit 1
fi

CLIENT_NAME=$1
CLIENT_SECRET=$2
CLIENT_CALLBACK=$3

uaac client add $CLIENT_NAME \
  --scope "openid" \
  --authorized_grant_types "authorization_code,refresh_token" \
  --authorities "uaa.none"  \
  --redirect_uri "$CLIENT_CALLBACK" \
  -s $CLIENT_SECRET
