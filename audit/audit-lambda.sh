#!/bin/bash

# Disable AWS pager so output goes straight to console
export AWS_PAGER=''

aws lambda list-functions --output table

for function_name in $(aws lambda list-functions --output json | jq -r '.Functions[].FunctionName'); do
  aws lambda get-policy --function-name "$function_name" --output table
done