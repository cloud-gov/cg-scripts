#!/bin/bash

minimum_log_age_for_deletion="30m"

for log_group_name in $(aws logs describe-log-groups --log-group-name-prefix "$1" | jq -r '.logGroups[].logGroupName'); do
  latest_event_timestamp=$(aws logs describe-log-streams --log-group-name "$log_group_name" \
    | jq -r '.logStreams | sort_by(.lastEventTimestamp) | last | .lastEventTimestamp')
  if (( (latest_event_timestamp / 1000) < $(date -v "-$minimum_log_age_for_deletion" +%s) )); then
    echo "deleting $log_group_name"
    aws logs delete-log-group --log-group-name "$log_group_name"
  fi
done
