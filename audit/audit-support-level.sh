#!/bin/bash

# Disable AWS pager so output goes straight to console
export AWS_PAGER=''

ACCOUNT_ID=$(aws sts get-caller-identity --output json | jq -r '.Account')
printf "account ID: %s\n" "$ACCOUNT_ID"

# See https://stackoverflow.com/a/73903651
SUPPORT_STATUS=$(aws support describe-severity-levels)
if [[ "$SUPPORT_STATUS" == *"SubscriptionRequiredException"* ]]; then
  echo "No Support Enabled for account"
elif [[ "$SUPPORT_STATUS" == *"AccessDeniedException"* ]]; then
  echo "Access denied or roles not properly setup"
elif [[ "$SUPPORT_STATUS" == *"critical"* ]]; then
  echo "Enterprise Support already enabled for account..."
elif [[ "$SUPPORT_STATUS" == *"urgent"* ]]; then
  echo "Only Business Level Support enabled for account..."
elif [[ "$SUPPORT_STATUS" == *"high"* ]]; then
  echo "Only Developer Level Support enabled for account..."
fi
