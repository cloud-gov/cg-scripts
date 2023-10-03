#!/bin/bash

function usage {
  echo -e "
  ./$( basename "$0" ) <IP_OR_HOSTNAME> <SEARCH_JSON_FILE> <'field1,field2'>

  Use the Elasticsearch/Opensearch scroll API to query logs for bulk export

  Examples:
    ./$( basename "$0" ) 127.0.0.1 search.json '."@timestamp",.rtr.path,.rtr.status'
  "
  exit
}

if [ -z "$1" ]; then
  echo "IP/hostname for Elasticsearch/Opensearch cluster is required as first argument"
  usage
fi

if [ -z "$2" ]; then
  echo "Filename containing search query JSON is required as second argument"
  usage
fi

if [ -z "$3" ]; then
  echo "String containing fields to extract into CSV is required as third argument"
  usage
fi

# Use port 9200
es_url="$1:9200"
search_json_file="$2"
csv_fields="$3"

get_hits_count() {
  echo "$1" | jq -r '.hits.hits | length'
}

get_scroll_id() {
  echo "$1" | jq -r '._scroll_id'
}

write_csv_output() {
  echo "$1" | jq ".hits.hits[]._source | [$csv_fields] | @csv" > "results-$2.csv"
}

response=$(curl -s -X POST "$es_url/_search?scroll=1m" \
  -H 'content-type: application/json' \
  -d "@$search_json_file")

hits_count=$(get_hits_count "$response")
hits_total=$(echo "$response" | jq -r '.hits.total.value')
hits_so_far=$hits_count
scroll_id=$(get_scroll_id "$response")
counter=1

echo "Got initial response with $hits_count hits out of $hits_total"

write_csv_output "$response" $counter

while [ "$hits_count" != "0" ]; do
  counter=$((counter + 1))

  response=$(curl -X POST -s -H 'content-type: application/json' "$es_url/_search/scroll" -d "{ \"scroll\": \"1m\", \"scroll_id\": \"$scroll_id\" }")
  
  scroll_id=$(get_scroll_id "$response")
  hits_count=$(get_hits_count "$response")
  hits_so_far=$((hits_so_far + hits_count))

  echo "Got response with $hits_count hits ($hits_so_far total hits so far out of $hits_total)"

  if [ "$hits_count" != "0" ]; then
    write_csv_output "$response" $counter
  fi
done

echo Done!

