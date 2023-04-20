#!/usr/bin/env bash

# Disable AWS pager so output goes straight to console
export AWS_PAGER=''

function update_offpeak_config {
  printf "\nprocessing domain %s\n" "$1"

  domain_config=$(aws opensearch describe-domain-config --domain-name "$1" | jq -r '.DomainConfig')
  created=$(echo "$domain_config" | jq -r '.EngineVersion.Status.CreationDate')
  auto_tune_offpeak_enabled=$(echo "$domain_config" | jq -r '.AutoTuneOptions.Options.UseOffPeakWindow // false')

  printf "domain %s, created %s, auto-tune off-peak enabled: %s\n" "$1" "$created" "$auto_tune_offpeak_enabled"

  update_options=""

  if  $auto_tune_offpeak_enabled; then
    printf "auto-tune off-peak enabled on domain\n"
    update_options="$update_options --auto-tune-options DesiredState=ENABLED,UseOffPeakWindow=false,MaintenanceSchedules=[]"
  else
    printf "auto-tune off-peak not enabled on domain %s, nothing to do\n" "$1"
  fi

  if [ -n "$update_options" ]; then
    printf "disabling off-peak window for auto-tune \n"
    
    # shellcheck disable=SC2086
    aws opensearch update-domain-config \
      --domain-name "$1" \
      $update_options > /dev/null
    
    printf "off-peak window disabled for domain %s\n" "$1"
  fi
}

if [ -z "$1" ]; then
  for domain_name in $(aws opensearch list-domain-names --output json | jq -r '.DomainNames[].DomainName'); do
    update_offpeak_config "$domain_name"
  done
else
  update_offpeak_config "$1"
fi
