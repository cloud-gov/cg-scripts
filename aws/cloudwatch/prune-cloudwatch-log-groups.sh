#!/bin/bash

LOG_GROUP_NAME_PREFIX="$1"
if [[ -z "$LOG_GROUP_NAME_PREFIX" ]]; then
  echo "log group name prefix is required as first argument"
  exit 1
fi

minimum_log_age_for_deletion="30m"

for log_group_name in $(aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP_NAME_PREFIX" | jq -r '.logGroups[].logGroupName'); do
  latest_event_timestamp=$(aws logs describe-log-streams --log-group-name "$log_group_name" \
    | jq -r '.logStreams | sort_by(.lastEventTimestamp) | last | .lastEventTimestamp')
  if (( (latest_event_timestamp / 1000) < $(date -v "-$minimum_log_age_for_deletion" +%s) )); then
    echo "deleting $log_group_name"
    aws logs delete-log-group --log-group-name "$log_group_name"
  fi
done
