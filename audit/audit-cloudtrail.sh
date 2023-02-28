#!/bin/bash

# Disable AWS pager so output goes straight to console
export AWS_PAGER=''

aws cloudtrail describe-trails --output table

for trail_arn in $(aws cloudtrail describe-trails --output json | jq -r '.trailList[].TrailARN');
do
  aws cloudtrail get-trail-status --name "$trail_arn" --output table
  aws cloudtrail get-event-selectors --trail-name "$trail_arn" --output table
  aws cloudtrail get-insight-selectors --trail-name "$trail_arn" --output table
done