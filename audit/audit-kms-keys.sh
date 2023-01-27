#!/bin/bash

# Disable AWS pager so output goes straight to console
export AWS_PAGER=''

# Output keys as table
aws kms list-keys --output table

for key_id in $(aws kms list-keys --output json | jq -r '.Keys[].KeyId'); do
  aws kms describe-key --key-id "$key_id" --output table

  aws kms get-key-rotation-status --key-id "$key_id" --output table

  aws kms list-key-policies --key-id "$key_id" --output table

  for policy_name in $(aws kms list-key-policies --key-id "$key_id" --output json | jq -r '.PolicyNames[]'); do
    aws kms get-key-policy --key-id "$key_id" --policy-name "$policy_name" --output table
  done
done
