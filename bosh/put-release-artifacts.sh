#!/usr/bin/env bash

function usage {
  echo -e "
  ./$( basename "$0" ) <release-name> <source-directory> <releases-bucket>

  Tar release artifacts from source directory and upload them to releases bucket.
  "
  exit
}


RELEASE_NAME="$1"
SOURCE_DIR="$2"
BOSH_RELEASES_BUCKET="$3"

if [[ -z "$RELEASE_NAME" ]]; then
  echo "release name is required as first argument. exiting."
  usage
fi

if [[ -z "$SOURCE_DIR" ]]; then
  echo "source directory is required as second argument. exiting."
  usage
fi

if [[ -z "$BOSH_RELEASES_BUCKET" ]]; then
  echo "BOSH releases bucket is required as third argument. exiting."
  usage
fi

release_tgz="releases-dir-${RELEASE_NAME}.tgz"
final_tgz="final-builds-dir-${RELEASE_NAME}.tgz"

pushd "$SOURCE_DIR" || exit 1

tar czf "${release_tgz}" ./releases
aws s3 cp --sse AES256 "${release_tgz}" "s3://${BOSH_RELEASES_BUCKET}/${release_tgz}" 

tar czf "${final_tgz}" ./.final_builds 
aws s3 cp  --sse AES256 "${final_tgz}" "s3://${BOSH_RELEASES_BUCKET}/${final_tgz}" 

popd
