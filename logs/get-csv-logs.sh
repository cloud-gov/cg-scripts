#!/bin/bash

set -euo pipefail

function usage {
  echo -e "
  ./$( basename "$0" ) <SEARCH_JSON_FILE> [CSV_FIELDS]

  Use the Elasticsearch/Opensearch scroll API to query logs for bulk export
  See full docs at: https://workshop.cloud.gov/cloud-gov/internal-docs/-/blob/main/docs/runbooks/Logging/bulk-data-export.md

  With Opensearch using TLS, run this from an an OpenSearch Manager node as the vcap user.

  Then use bosh ssh to copy the file to the jumpbox, and from there to your local machine.

  Examples:
    ./$( basename "$0" ) search.json
  "
  exit
}

JOB_NAME=opensearch
JOB_DIR=/var/vcap/jobs/$JOB_NAME
CSV_FIELDS='."@timestamp",."@raw"'
ES_URL="localhost:9200"
CERT_PATH="${JOB_DIR}/config/ssl/opensearch-admin.crt"
KEY_PATH="${JOB_DIR}/config/ssl/opensearch-admin.key"
CA_PATH="${JOB_DIR}/config/ssl/opensearch.ca"
OUTPUT_DIR="/var/vcap/store/export"
OUTPUT_FILE="$OUTPUT_DIR/logs_export.csv"
SCROLL_TIMEOUT="15m"
BATCH_SIZE=10000

if [ -z "$1" ]; then
  echo "Filename containing search query JSON is required as second argument"
  usage
fi

SEARCH_JSON_FILE="$1"

# Optional second argument to specify which fields to include in the CSV output, as a comma-separated list of jq field expressions
if [ $# -eq 2 ]; then
  CSV_FIELDS="$2"
fi

get_hits_count() {
  echo "$1" | jq -r '.hits.hits | length'
}

get_scroll_id() {
  echo "$1" | jq -r '._scroll_id'
}

write_csv_output() {
  echo "$1" | jq -r ".hits.hits[]._source | [$CSV_FIELDS] | @csv" >> $OUTPUT_FILE
}

## ------ ## Main script starts here ## ------ ##

# Write CSV header
echo $CSV_FIELDS > $OUTPUT_FILE

response=$(curl -s -X POST "https://$ES_URL/_search?scroll=$SCROLL_TIMEOUT&size=$BATCH_SIZE" \
  --cert "$CERT_PATH" \
  --key "$KEY_PATH" \
  --cacert "$CA_PATH" \
  -H 'Content-Type: application/json' \
  -d @search.json)

hits_count=$(get_hits_count "$response")
hits_total=$(echo "$response" | jq -r '.hits.total.value')
hits_so_far=$hits_count
scroll_id=$(get_scroll_id "$response")

echo "Got initial response with $hits_count hits out of $hits_total"

write_csv_output "$response"

while true; do
  response=$(curl -s -X POST "https://$ES_URL/_search/scroll" \
    --cert "$CERT_PATH" \
    --key "$KEY_PATH" \
    --cacert "$CA_PATH" \
    -H 'Content-Type: application/json' \
    -d "{\"scroll\":\"$SCROLL_TIMEOUT\",\"scroll_id\":\"$scroll_id\"}")

  scroll_id=$(get_scroll_id "$response")
  hits_count=$(get_hits_count "$response")
  hits_so_far=$((hits_so_far + hits_count))

  if [ $hits_count -eq 0 ]; then
    break
  fi

  echo "Got response with $hits_count hits ($hits_so_far total hits so far out of $hits_total)"
  write_csv_output "$response"
done

# Clean up scroll context
curl -s -X DELETE "https://$ES_URL/_search/scroll" \
  --cert "$CERT_PATH" \
  --key "$KEY_PATH" \
  --cacert "$CA_PATH" \
  -H 'Content-Type: application/json' \
  -d "{\"scroll_id\":\"$scroll_id\"}" > /dev/null

gzip -v "$OUTPUT_FILE"

echo Done!

