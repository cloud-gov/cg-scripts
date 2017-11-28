#!/bin/bash

set -eu

if [ "$#" -lt 4 ]; then
  echo "es-scroll-search.sh - query across elasticsearch indexes and save results to .zip"
  echo
  echo "  Usage:"
  echo "    $ ./es-scroll-search.sh [-s] elasticsearch-ip index-pattern query-file save-path"
  echo
  echo "            See included es-scroll-search-query.json for example query"
  echo
  echo "  Options:"
  echo "    -s  :   Upload results to S3 bucket and remove local files"
  echo "            using env AWS_DEFAULT_REGION, BUCKET_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
  echo "            (see https://cloud.gov/docs/services/s3/)"
  echo
  exit 99
fi
S3=false

while getopts ":s" opt; do
  case $opt in
    s)
      S3=true
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1;
      ;;
  esac
done

ES_IP="${BASH_ARGV[3]}"
INDEX_PATTERN="${BASH_ARGV[2]}"
QUERY_FILE="${BASH_ARGV[1]}"
SAVE_PATH="${BASH_ARGV[0]}"

search() {

  index="${1}"

  # open up a search context with query.json
  response=$(curl -s "${ES_IP}:9200/$index/_search?scroll=1m" -d "@${QUERY_FILE}")
  scroll_id=$(echo $response | jq -r ._scroll_id)
  hits_count=$(echo $response | jq -r '.hits.hits | length')

  # save off response in .zip
  echo $response > ${SAVE_PATH}/${index}-0.json
  zip ${SAVE_PATH}/${index}-0.json.zip ${SAVE_PATH}/${index}-0.json
  rm ${SAVE_PATH}/${index}-0.json

  # scroll and save until there are no more records
  file_count=0
  while [ "$hits_count" != "0" ]; do
    file_count=$((file_count+1))

    response=$(curl -s "${ES_IP}:9200/_search/scroll" -d "{ \"scroll\": \"1m\", \"scroll_id\": \"$scroll_id\" }")
    scroll_id=$(echo $response | jq -r ._scroll_id)
    hits_count=$(echo $response | jq -r '.hits.hits | length')

    echo $response > ${SAVE_PATH}/${index}-${file_count}.json
    zip ${SAVE_PATH}/${index}-${file_count}.json.zip ${SAVE_PATH}/${index}-${file_count}.json
    rm ${SAVE_PATH}/${index}-${file_count}.json

  done
}

# create the save_path
mkdir -p $SAVE_PATH

curl -s "${ES_IP}:9200/_cat/indices" | awk '{print $3}' | grep "${INDEX_PATTERN}" | while read index; do

  # search the index and save to local .zip files
  search "${index}"

  # upload to s3 and remove local files
  if $S3; then
    aws s3 sync ${SAVE_PATH} s3://${BUCKET_NAME} --sse AES256
    rm -f "${SAVE_PATH}/${index}*.zip"
  fi

done
