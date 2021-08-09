#!/usr/bin/env bash

set -euo pipefail

function days_to_cert_expiration {
  local expirationdate=$1;
  local date_today=$(gdate +%s);


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

lb_arns=()
lb_selector='.LoadBalancers[] | select(.LoadBalancerName | startswith($prefix)) | .LoadBalancerArn'
lbs=$(aws elbv2 describe-load-balancers)
for lb_arn in $(echo "${lbs}" | jq -r --arg prefix "${PREFIX}" "${lb_selector}"); do
  lb_arns+=("${lb_arn}")
done
next_token=$(echo "${lbs}" | jq -r '.NextToken // ""')
while [ -n "${next_token}" ]; do
  lbs=$(aws elbv2 describe-load-balancers --starting-token "${next_token}")
  for lb_arn in $(echo "${lbs}" | jq -r --arg prefix "${PREFIX}" "${lb_selector}"); do
    lb_arns+=("${lb_arn}")
  done
  next_token=$(echo "${lbs}" | jq -r '.NextToken // ""')
done

nlbs=0
ncerts=0
alb_listeners=""
cert_expirations=""
for lb_arn in "${lb_arns[@]}"; do
  lb_listener_arns=$(aws elbv2 describe-listeners --load-balancer-arn "${lb_arn}" \
      | jq -r ".Listeners[] | select(.Port == 443) | .ListenerArn")
  for lb_listener_arn in ${lb_listener_arns}; do
    nlbs=$((nlbs + 1))
    certs_listener=$(aws elbv2 describe-listener-certificates --listener-arn "${lb_listener_arn}")
    cert_names="$(echo ${certs_listener} | jq -r '.Certificates[] | .CertificateArn'  | awk -F/ '{ print $NF }')"
      for cert_name in ${cert_names}; do
        cert_metadata=$(aws iam get-server-certificate --server-certificate-name ${cert_name})
        cert_date=$(echo "${cert_metadata}" | jq -r '.ServerCertificate | .ServerCertificateMetadata | .Expiration')
        cert_expiration=$(gdate --date "${cert_date}" +%s)
        days_left=$(days_to_cert_expiration $cert_expiration)
        if [[ ${days_left} -lt 25 ]]; then
          # run the the renewal || true, so we keep doing all of them even if there's a failure
          python3 alb_certs.py --alb-listener-arn "${lb_listener_arn}" --cert-name "${cert_name}" || /bin/true
        fi
      done
  done
done
