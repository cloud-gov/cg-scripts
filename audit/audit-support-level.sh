#!/bin/bash

# Disable AWS pager so output goes straight to console
export AWS_PAGER=''

ACCOUNT_ID=$(aws sts get-caller-identity --output json | jq -r '.Account')

# See https://stackoverflow.com/a/73903651
SUPPORT_STATUS=$(aws support describe-severity-levels)
SUPPORT_LEVEL=""
if [[ "$SUPPORT_STATUS" == *"SubscriptionRequiredException"* ]]; then
  SUPPORT_LEVEL="No Support Enabled for account"
elif [[ "$SUPPORT_STATUS" == *"AccessDeniedException"* ]]; then
  SUPPORT_LEVEL="Access denied or roles not properly setup"
elif [[ "$SUPPORT_STATUS" == *"critical"* ]]; then
  SUPPORT_LEVEL="Enterprise"
elif [[ "$SUPPORT_STATUS" == *"urgent"* ]]; then
  SUPPORT_LEVEL="Business"
elif [[ "$SUPPORT_STATUS" == *"high"* ]]; then
  SUPPORT_LEVEL="Developer"
fi

echo "$ACCOUNT_ID,$SUPPORT_LEVEL"
