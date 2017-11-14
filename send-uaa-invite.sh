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

echo "Invite link: ${link}"
