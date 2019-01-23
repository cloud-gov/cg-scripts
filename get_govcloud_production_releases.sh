#!/bin/bash

set -e

all_buildpacks=$(cf buildpacks | tail -n +4 | awk '{print $1 ": " $5}' | grep '\_buildpack:')

echo "${all_buildpacks}" |\
  sed 's/_buildpack//' |\
  sed -E 's/([a-z-]+[\-\_])buildpack-/\1/' |\
  sed 's/.zip/: /' |\
  sed 's/_/-/g' |\
  sed -E 's/(^[a-z\-]+): .*(v[0-9.]+):/https:\/\/github.com\/cloudfoundry\/\1-buildpack\/releases\/tag\/\2/g'

echo "https://github.com/cloudfoundry/cflinuxfs2/releases"
echo "https://github.com/cloudfoundry/bosh-linux-stemcell-builder/releases"
echo "https://github.com/cloudfoundry/diego-release/releases"
echo "https://github.com/cloudfoundry/cf-deployment/releases"
echo "https://github.com/cloudfoundry/capi-release/releases"
echo "https://www.cloudfoundry.org/foundryblog/security-advisory/"
