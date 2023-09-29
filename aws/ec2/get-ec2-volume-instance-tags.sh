#!/bin/bash

# Disable AWS pager so output goes straight to console
export AWS_PAGER=''

if [ -z "$1" ]; then
  echo "Filter name is required as first argument."
  exit 1
fi

if [ -z "$2" ]; then
  echo "Filter value(s) are required as second argument."
  exit 1
fi

TAGS="Name,deployment"
TAGS_FILTER=$(IFS=','; for tag in $TAGS; do echo \"$tag\"; done)

echo $TAGS_FILTER

# for instance_id in $(aws ec2 describe-volumes --filters="Name=$1,Values=$2" --output json | jq -r '.Volumes[].Attachments[].InstanceId'); do
#   aws ec2 describe-tags --filters "Name=resource-id,Values=$instance_id" | jq '.Tags[] | select(.Key==("Name", "deployment")) | .Key + ":" + .Value'
#   printf "\n"
# done

