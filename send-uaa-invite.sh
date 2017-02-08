#!/bin/sh

set -e

if [ "$#" -lt 1 ]; then
  printf "Usage:\n\n\t$./send-uaa-invite.sh <USER_EMAIL>"
  exit 1
fi

redirect_uri=https://account.fr.cloud.gov/oauth/login
fugacious_uri=https://fugacious.18f.gov

resp=$(uaac curl -X POST "/invite_users?redirect_uri=${redirect_uri}" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --arg email $1 '{emails: [$email]}')")

error=$(echo ${resp#*RESPONSE BODY:} | jq -r '.error // ""')

if [[ -n ${error} ]]; then
  echo "error: $error"
  exit 1
fi

link=$(echo ${resp#*RESPONSE BODY:} | jq -r '.new_invites[0].inviteLink')

fug=$(curl -i ${fugacious_uri}/m \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -d "$(jq -n --arg body ${link} '{message: {body: $body, hours: 24, max_views: 2}}')" \
  | grep Location \
  | awk '{print $2}')

echo "Created ephemeral invite link at: ${fug}"
