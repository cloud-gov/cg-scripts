#!/bin/bash

function usage {
  echo -e "
  ./$( basename "$0" ) <environment> <output-directory> <filename>

  Generates and downloads a BOSH inventory list from a jumpbox.

  Optional environment variable \$CI_URL matching your Concourse URL.
  example: CI_URL=https://ci.fr.cloud.gov ./$( basename "$0" )

  \$CI_URL, Defaults to https://ci.fr.cloud.gov

  Examples:
    ./$( basename "$0" ) production ~/Downloads inv.csv
  "
  exit
}

if [ -z "$1" ]; then
  echo "Environment (e.g. development, staging, production) required as first argument"
  usage
fi

if [ -z "$2" ]; then
  echo "Output directory for file required as second argument"
  usage
fi

if [ -z "$3" ]; then
  echo "Filename to copy output to required for third argument"
  usage
fi

ENVIRONMENT=$1
OUTPUT_DIR=$2
FILE=$3

CI_URL="${CI_URL:-"https://ci.fr.cloud.gov"}"
FLY_TARGET=$(fly targets | grep "${CI_URL}" | head -n 1 | awk '{print $1}')

JUMPBOX_CONTAINER="container-bosh-${ENVIRONMENT}"
BUILD_NUMBER=$(fly -t "$FLY_TARGET" containers | grep jumpbox | grep "$JUMPBOX_CONTAINER" | awk '{print $5}' | sort -nr | head -n 1)

echo "Attempting to generate inventory and download file from $JUMPBOX_CONTAINER, build ${BUILD_NUMBER}"

fly -t "$FLY_TARGET" i -j "jumpbox/$JUMPBOX_CONTAINER" -s jumpbox -b "$BUILD_NUMBER" -- python3 cg-scripts/generate-POAM-inventory.py > "$OUTPUT_DIR/$FILE"

echo "successfully downloaded $FILE"
