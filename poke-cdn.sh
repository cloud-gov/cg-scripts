#!/bin/bash

# Force a cdn broker instance into the `provisioned` state so that it can be deleted
# Usage: `DOMAIN="some.domain.gov" ./poke-cdn.sh`

set -e
set -u
set -x

if ! cf plugins | grep "connect-to-service"; then
  echo "connect-to-service plugin not found; install at https://github.com/18F/cf-service-connect#local-installation"
  exit 1
fi

cf target -o ${ORG:-cloud-gov} -s ${SPACE:-services}
echo "update routes set state = 'provisioned' where domain_external = '${DOMAIN}' and state = 'provisioning'" \
  | cf connect-to-service ${APP:-cdn-broker} ${DATABASE:-rds-cdn-broker}
