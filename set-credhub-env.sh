#!/bin/bash

set -e

if [ "$#" -lt 1 ]
then
  echo "Usage:"
  echo "    ./set-credhub-env.sh <BOSH_DEPLOYMENT_NAME>"
  echo "example: ./set-credhub-env.sh developmentbosh"
  exit 99
fi

deployment_name=$(bosh deployments | grep -o "${1}")

if [ "$?" -eq 0 ]
then
  echo "setting up CredHub environment for ${deployment_name}"
  ch_grabbed_secret="$(
    bosh -d "${deployment_name}" manifest |\
    spruce json |\
    jq -r '.instance_groups[].jobs[] | select( .name == "uaa") | .properties.uaa.clients["credhub-admin"].secret'
  )"
  ch_grabbed_server="$(
    bosh -d "${deployment_name}" manifest |\
    spruce json |\
    jq -r '.instance_groups[].properties.director.config_server.url'
  )"
  export CREDHUB_CLIENT='credhub-admin'
  export CREDHUB_SECRET="${ch_grabbed_secret}"
  export CREDHUB_CA_CERT=$BOSH_CA_CERT
  export CREDHUB_SERVER="${ch_grabbed_server}"
fi
