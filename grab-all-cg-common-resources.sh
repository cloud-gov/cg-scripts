#!/bin/bash

audit_time=$( date "+%Y-%m-%dT%H:%M:%S" )
file_name="cg-common-state-passphrases-${audit_time}.json"

echo "{" >> $file_name
for pipeline in $(fly --target fr pipelines | grep -Eo '^[a-z0-9\-]+' | grep 'deploy')
do
  hash=$(fly --target fr get-pipeline --pipeline $pipeline --json |
  jq -er '.resources[] | select( .name | test( "common-?" ) ) | { "name": .name, "secrets_files": .source.secrets_files, "secrets_file": .source.secrets_file, "passphrase": .source.secrets_passphrase, "bucket": .source.bucket_name }' |
  jq -s '.')
  echo
  echo -n "\"${pipeline}\": "
  echo -n $hash
  echo ","
done | tee -a $file_name
echo "\"generated_at\": \"${audit_time}\"" >> $file_name
echo "}" >> $file_name

