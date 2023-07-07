#!/bin/bash

function usage {
cat >&2 <<EOM

usage: $(basename "$0") <log-group-name-prefix>

options:

  $0 -d          Set this value if you want to delete log groups with no logs newer than the given timestamp
  $0 -a          Set timestamp (in seconds) that will be used to flag log groups for deletion. Defaults to flagging log groups with no new logs in the last 30 months.

Query AWS to find and optionally delete Cloudwatch log groups which don't have newer logs than the given timestamp.
EOM
}

MINIMUM_LOG_AGE_TIMESTAMP=$(date -v "-30m" +%s)
DELETE=0

while getopts ":hda:" opt; do
  case ${opt} in
    h )
      usage
      exit 0
      ;;
    d )
      DELETE=1
      ;;
    a )
      MINIMUM_LOG_AGE_TIMESTAMP=$OPTARG
      ;;
    * )
      echo "Invalid Option: $OPTARG"
      usage
      exit 1
      ;;
  esac
done
shift $((OPTIND -1))

LOG_GROUP_NAME_PREFIX="$1"
if [[ -z "$LOG_GROUP_NAME_PREFIX" ]]; then
  echo "log group name prefix is required as first argument"
  exit 1
fi

for log_group_name in $(aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP_NAME_PREFIX" | jq -r '.logGroups[].logGroupName'); do
  latest_event_timestamp=$(aws logs describe-log-streams --log-group-name "$log_group_name" \
    | jq -r '.logStreams | sort_by(.lastEventTimestamp) | last | .lastEventTimestamp')
  if (( (latest_event_timestamp / 1000) < MINIMUM_LOG_AGE_TIMESTAMP )); then
    MINIMUM_LOG_AGE_DATE=$(date -r "$MINIMUM_LOG_AGE_TIMESTAMP")
    echo "$log_group_name has no logs newer than $MINIMUM_LOG_AGE_DATE"
    if (( DELETE > 0 )); then
      echo "deleting $log_group_name"
      aws logs delete-log-group --log-group-name "$log_group_name"
    fi
  fi
done
