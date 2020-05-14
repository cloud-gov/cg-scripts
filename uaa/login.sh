#!/bin/bash

set -e

pushd () {
  command pushd "$@" > /dev/null
}

popd () {
  command popd "$@" > /dev/null
}

main() {
  # This needs to run from the directory you are logged into when
  # connecting to a jumpbox because of certs.
  this_directory=$(dirname "$0")
  pushd ${this_directory}/../..
    local environment_name="${BOSH_DIRECTOR_NAME,,}"

    if [ "$environment_name" == "production" ]; then
      local target="uaa.fr.cloud.gov"
    elif [ "$environment_name" == "staging" ]; then
      credhub login --skip-tls-validation
      local target="uaa.fr-stage.cloud.gov"
    elif [ "$environment_name" == "development" ]; then
      local target="uaa.dev.us-gov-west-1.aws-us-gov.cloud.gov"
    else
      echo "ERROR: Unknown environment ${environment_name}"
      exit 1
    fi

    local admin_pwd=$(credhub get -n "/bosh/cf-${environment_name}/uaa_admin_client_secret" | grep value | sed -r 's/value: //g')
    uaac target $target
    uaac token client get admin -s $admin_pwd
  popd
}

main