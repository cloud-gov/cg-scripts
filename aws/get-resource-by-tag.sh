#!/bin/bash

function usage {
cat >&2 <<EOM

usage: $(basename "$0") <tag-value>

options:

  $0 -h          Display this help message.
  $0 -t          Set the tag name to search for resources by. Defaults to "Instance GUID".
  $0 -r          Set the resource type (e.g. "opensearch", "rds"). Defaults to "rds".

Query AWS by tag value to find AWS resources. Currently supports RDS, Opensearch, and S3.
EOM
}

RESOURCE_TYPE="rds"
TAG_NAME="Instance GUID"

while getopts ":hr:t:" opt; do
  case ${opt} in
    h )
      usage
      exit 0
      ;;
    t )
      TAG_NAME=$OPTARG
      ;;
    r )
      RESOURCE_TYPE=$OPTARG
      ;;
    * )
      echo "Invalid Option: $OPTARG"
      usage
      exit 1
      ;;
  esac
done
shift $((OPTIND -1))

TAG_VALUE="$1"
if [[ -z "$TAG_VALUE" ]]; then
  echo "Tag value must be specified as first argument to script."
  usage
  exit 1
fi

case ${RESOURCE_TYPE} in
  opensearch | elasticsearch | es )
    RESOURCE_TYPE_FILTER="es:domain"
    ;;
  rds )
    RESOURCE_TYPE_FILTER="rds:db"
    ;;
  s3 )
    RESOURCE_TYPE_FILTER="s3:bucket"
    ;;
  redis | elasticache )
    RESOURCE_TYPE_FILTER="elasticache:replicationgroup"
    ;;
  * )
    echo "Invalid option: $RESOURCE_TYPE" >&2
    usage
    exit 1
    ;;
esac

aws resourcegroupstaggingapi get-resources \
  --resource-type-filters "$RESOURCE_TYPE_FILTER" \
  --tag-filters Key="$TAG_NAME",Values="$TAG_VALUE" \
  | jq '.ResourceTagMappingList[].ResourceARN'
