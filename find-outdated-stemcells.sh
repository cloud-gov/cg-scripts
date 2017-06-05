#!/bin/bash
target="fr"
if [ "$1" = '-v' ]; then
  VERBOSE=1
fi

verbose(){
  [ "${VERBOSE}x" = "1x" ] && echo "$1: ${!1}"
}

published_stemcell=$(curl https://bosh.io/api/v1/stemcells/bosh-aws-xen-ubuntu-trusty-go_agent -s |
  jq -r '[.[]| .version | capture("(?<a>[0-9]+).(?<b>[0-9]+)")] | max_by(.a,.b|tonumber) | .a + "." + .b')

verbose published_stemcell

# TODO: Use last-modified on stemcel to determine if Nessus should be rebuilt
# curl -vso /dev/null https://s3.amazonaws.com/bosh-core-stemcells/aws/bosh-stemcell-3312.28-aws-xen-ubuntu-trusty-go_agent.tgz 2>&1 | grep Last-Modified

current_stemcell=$(fly -t fr watch --job  aws-light-stemcell-builder/publish-ubuntu-hvm | 
    perl -ne 'm/^version: "([\d\.]+)"/ && print $1')
verbose current_stemcell

if [ $current_stemcell != $published_stemcell ]; then
  echo "ERROR: stemcell versions are out of sync:"
  echo "  Current bosh.io stemcell version is $published_stemcell"
  echo "  Current internally available verion is $current_stemcell"
  echo "Be sure the job, aws-light-stemcell-builder/publish-ubuntu-hvm, is running correctly"
  echo "Exiting..."
  exit 0
fi

echo "Finding deployments with stemcells that don't match current version, $published_stemcell"
for env in development tooling staging production; do 
  echo ======== $env =========
    build="$(fly -t $target tj -j "jumpbox/container-bosh-$env" -w | grep started | cut -d'#' -f2 | tr -d '\r \n')"
    verbose build
    # Don't rebuild nessus just yet...
    fly -t $target i -j "jumpbox/container-bosh-$env" -s jumpbox -b $build -- bosh-cli deployments | 
        grep aws-xen | grep -v $current_stemcell | grep -vi nessus
done
