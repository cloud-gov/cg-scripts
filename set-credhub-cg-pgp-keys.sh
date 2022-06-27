#!/usr/bin/env bash

if [ -z "$GITHUB_USERNAME" ]; then
    echo "GITHUB_USERNAME is required"
    exit 1
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "GITHUB_TOKEN is required"
    exit 1
fi

TEAM="cloud-gov-team"

USERS=$(curl -u "$GITHUB_USERNAME:$GITHUB_TOKEN" \
    "https://api.github.com/orgs/cloud-gov/teams/${TEAM}/members" \
    | jq -r '.[].login')

for user in $USERS; do
    curl  -u "$GITHUB_USERNAME:$GITHUB_TOKEN" \
        "https://api.github.com/users/$user/gpg_keys" \
        | jq '.[].raw_key | select(.emails[].email | contains ("gsa.gov"))'
done