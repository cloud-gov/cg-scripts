#!/bin/bash

function usage {
  echo -e "
  ./$( basename "$0" ) <release-name> <target-directory> <releases-bucket>

  Download BOSH release artifacts from S3 and untar them to the target directory.
  "
  exit
}


RELEASE_NAME="$1"
TARGET_DIR="$2"
BOSH_RELEASES_BUCKET="$3"

if [[ -z "$RELEASE_NAME" ]]; then
  echo "release name is required as first argument. exiting."
  usage
fi

if [[ -z "$TARGET_DIR" ]]; then
  echo "target directory is required as second argument. exiting."
  usage
fi

if [[ -z "$BOSH_RELEASES_BUCKET" ]]; then
  echo "BOSH releases bucket is required as third argument. exiting."
  usage
fi

cd "$TARGET_DIR" || exit 1

aws s3 cp "s3://$BOSH_RELEASES_BUCKET/releases-dir-$RELEASE_NAME.tgz" .
tar xvzf "releases-dir-$RELEASE_NAME.tgz"

aws s3 cp "s3://$BOSH_RELEASES_BUCKET/final-builds-dir-$RELEASE_NAME.tgz" .
tar xvzf "final-builds-dir-$RELEASE_NAME.tgz"
