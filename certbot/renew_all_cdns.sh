#!/usr/bin/env bash

set -euxo pipefail

## Calculate the days to expiration from now
function days_to_cert_expiration {
  local cloudfront=$1;
  local alias=$2;
  local date_today=$(gdate +%s);

  ## Get expirationdate and convert to epoch
  expirationdate=$(gdate -d "$(: | openssl s_client -connect $cloudfront:443 -servername $alias 2>/dev/null \
    | openssl x509 -text \
    | grep 'Not After' \
    | awk '{print $4,$5,$7}')" '+%s');

  ## Check the seconds to expiration from now
  seconds_to_go=$(expr $expirationdate - $date_today)\

  if ! [[ $seconds_to_go -gt 0 ]]; then
    ## Return integer less than or equal to 0
    seconds_past=$(expr $date_today - $expirationdate)
    negative_days=$(($seconds_past / 86400))
    echo $((0 - $negative_days))
  else
     ## Return integer greater than or equal to 0
    echo $(($seconds_to_go / 86400))
  fi
}

## Select and get Cloudfront instances returning ARN, & Aliases
alias_count=0
cdn_count=0
cdns_selector='.DistributionList.Items[] | select(.Aliases.Items != null) | {id:.Id,arn:.ARN,aliases:.Aliases.Items,domain:.DomainName}'
cdns=$(aws cloudfront list-distributions | jq -c "${cdns_selector}")
cdn_list=($cdns)

## Loop through list of CDN instances
cdn_certificate_expirations=""
for cdn in "${cdn_list[@]}"; do
  cdn_count=$((cdn_count + 1))
  aliases=($(echo $cdn | jq -r ".aliases[]"))
  arn=($(echo $cdn | jq -r ".arn"))
  domain=($(echo $cdn | jq -r ".domain"))
  id=($(echo $cdn | jq -r ".id"))

  for alias in "${aliases[@]}"; do
    alias_count=$((alias_count + 1))
    days_to_expire=$(days_to_cert_expiration $domain $alias)
    if [[ $days_to_expire -lt 25 ]]; then
      echo "${id} expires in ${days_to_expire}"
      cdn_certificate_expirations="${cdn_certificate_expirations} ${id}"
    fi
  done
done
cdn_certificate_expirations=$(echo ${cdn_certificate_expirations} | sort | uniq)

python3 cdn_certs.py --cdn-ids ${cdn_certificate_expirations}
