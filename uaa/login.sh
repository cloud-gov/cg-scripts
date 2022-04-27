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
    elif [ "$environment_name" == "westb" ]; then
      local target="uaa.fr.wb.cloud.gov"
    elif [ "$environment_name" == "westc" ]; then
      local target="uaa.fr.wc.cloud.gov"
    elif [ "$environment_name" == "easta" ]; then
      local target="uaa.fr.ea.cloud.gov"
    elif [ "$environment_name" == "eastb" ]; then
      local target="uaa.fr.eb.cloud.gov"
    elif [ "$environment_name" == "staging" ]; then
      local target="uaa.fr-stage.cloud.gov"
    elif [ "$environment_name" == "development" ]; then
      local target="uaa.dev.us-gov-west-1.aws-us-gov.cloud.gov"
    elif [ "$environment_name" == "tooling-east" ]; then
      local target="opslogin.fr.east.cloud.gov"
    elif [ "$environment_name" == "tooling-west" ]; then
      local target="opslogin.fr.west.cloud.gov"
    elif [ "$environment_name" == "tooling" ]; then
      local target="opslogin.fr.cloud.gov"
    else
      echo "ERROR: Unknown environment ${environment_name}"
      exit 1
    fi

    if [ "$environment_name" == "tooling" ]; then
      local admin_pwd=$(credhub get -n "/toolingbosh/opsuaa/uaa_admin_client_secret" | grep value | sed -r 's/value: //g')
    elif [ "$environment_name" == "tooling-east" ]; then
      local admin_pwd=$(credhub get -n "/tooling-east-bosh/opsuaa/uaa_admin_client_secret" | grep value | sed -r 's/value: //g')
    elif [ "$environment_name" == "tooling-west" ]; then
      local admin_pwd=$(credhub get -n "/tooling-west-bosh/opsuaa/uaa_admin_client_secret" | grep value | sed -r 's/value: //g')
    else
      local admin_pwd=$(credhub get -n "/bosh/cf-${environment_name}/uaa_admin_client_secret" | grep value | sed -r 's/value: //g')
    fi
    uaac target $target
    uaac token client get admin -s "$admin_pwd"
  popd
}
main