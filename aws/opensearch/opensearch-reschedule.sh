#!/usr/bin/env bash

# Disable AWS pager so output goes straight to console
export AWS_PAGER=''

function usage {
  echo -e "
  ./$( basename "$0" ) [--help, -h]

  Reschedule pending Opensearch domain upgrades for a given action ID

  Required environment variable \$ACTION_ID matching the action ID that you want to reschedule

  Examples:

    ACTION_ID=action-1 ./$( basename "$0" )
  "
  exit
}

if [ -z "$ACTION_ID" ]; then
  echo "Action ID to reschedule required as environment variable."
  usage
fi

while getopts "h" opt; do
  case ${opt} in
    h )
        usage
        exit 0
        ;;
    * )
        usage
        exit 0
        ;;
  esac
done

function reschedule_actions {
  printf "\nprocessing domain %s\n" "$1"

  for action_info in $(aws opensearch list-scheduled-actions --domain-name "$1" --output json | jq --arg action_id "$ACTION_ID" -r '.ScheduledActions[] | select(.Id==$action_id) | .Id + "," + .Type'); do
    IFS=',' read -r -a array <<< "$action_info"
    action_id="${array[0]}"
    action_type="${array[1]}"

    if [ -n "$action_id" ] && [ -n "$action_type" ]; then
      aws opensearch update-scheduled-action \
        --domain-name "$1" \
        --action-id "$action_id" \
        --action-type "$action_type" \
        --schedule-at "OFF_PEAK_WINDOW"
    fi
  done
}

if [ -z "$1" ]; then
  for domain_name in $(aws opensearch list-domain-names --output json | jq -r '.DomainNames[].DomainName'); do
    reschedule_actions "$domain_name"
  done
else
  reschedule_actions "$1"
fi
