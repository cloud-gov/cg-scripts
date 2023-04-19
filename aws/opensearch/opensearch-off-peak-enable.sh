#!/usr/bin/env bash

# Disable AWS pager so output goes straight to console
export AWS_PAGER=''

function update_offpeak_config {
  printf "\nprocessing domain %s\n" "$1"

  domain_config=$(aws opensearch describe-domain-config --domain-name "$1" | jq -r '.DomainConfig')
  offpeak_enabled=$(echo "$domain_config" | jq -r '.OffPeakWindowOptions.Options.Enabled // false')

  update_options=""

  if $offpeak_enabled; then
    printf "off-peak window already enabled for domain %s, nothing to do\n" "$1"
  else
    update_options="--off-peak-window-options Enabled=true"
  fi

  if [ -n "$update_options" ]; then
    # shellcheck disable=SC2086
    aws opensearch update-domain-config \
      --domain-name "$1" \
      $update_options > /dev/null
    
    printf "off-peak window and auto-tune configuration enabled for domain %s\n" "$1"
  fi
}

if [ -z "$1" ]; then
  for domain_name in $(aws opensearch list-domain-names --output json | jq -r '.DomainNames[].DomainName'); do
    update_offpeak_config "$domain_name"
  done
else
  update_offpeak_config "$1"
fi
