#!/bin/bash

set -e
set -u
# REQUIRES:
# env: UAA_URL
#      CLIENT_ID
#      CLIENT_SECRET


get_client_token() {
  TOKEN=$(curl -X POST -u "$CLIENT_ID:$CLIENT_SECRET" -H "Accept: application/json" -d "client_id=$CLIENT_ID&grant_type=client_credentials&response_type=token&token_format=opaque" "$UAA_URL/oauth/token" 2>/dev/null | sed -n 's/.*access_token":"\([^"]*\).*/\1/p')
}

process_user_tokens() {
  local start="$1"

  USERS_RESP=$(curl -X GET -H "Authorization: Bearer ${TOKEN}" -H "Accept: application/json" "${UAA_URL}/Users?sortBy=userName&sortOrder=ascending&startIndex=${start}" 2>/dev/null)
  TOTAL_RESULTS=$(echo "${USERS_RESP}" | jq --raw-output ".totalResults | tonumber")
  ITEMS_PER_PAGE=$(echo "${USERS_RESP}" | jq --raw-output ".itemsPerPage | tonumber")

  USERS=$(echo "$USERS_RESP" | jq --unbuffered --raw-output --compact-output ".resources[] | {id, userName}")
  for user in $USERS; do
    user_id=$(echo "$user" | jq --raw-output ".id | tostring")
    user_name=$(echo "$user" | jq --raw-output ".userName | tostring")
    user_tokens=$(curl -X GET -H "Authorization: Bearer ${TOKEN}" -H "Accept: application/json" "${UAA_URL}/oauth/token/list/user/${user_id}" 2>/dev/null)
    clients=$(echo "$user_tokens" | jq --compact-output "group_by(.clientId) | .[] | { id: (.[0].clientId), count: length, is_admin: (.[0].scope | contains(\"admin\")) }")
    for client in $clients; do
      count=$(echo $client | jq --raw-output ".count | tonumber" )
      client_id=$(echo $client | jq --raw-output ".id")
      if [ $(echo $client | jq ".is_admin") == 'true' ]; then
        if [ $count -gt 3 ]; then
          # notify
          echo $user_name
          echo "  ADMIN sessions: $client_id $count"
        fi
      else
        if [ $count -gt 2 ]; then
          # notify
          echo $user_name
          echo "  NON-PRIV sessions $client_id $count"
        fi
      fi
    done

  done

  HAS_NEXT_PAGE=false
  NEXT_PAGE_START=$(($start + $ITEMS_PER_PAGE))
  if [ "$TOTAL_RESULTS" -ge "$NEXT_PAGE_START" ]; then
    HAS_NEXT_PAGE=true
  fi
  if $HAS_NEXT_PAGE; then
    process_user_tokens $NEXT_PAGE_START
  fi
}

get_client_token
process_user_tokens 1
