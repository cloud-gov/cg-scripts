#!/bin/bash

if [ -z $1 ]; then
  echo
  echo "Usage:"
  echo "    $ ./bosh-audit.sh <after-date>"
  echo
  exit 1;
fi

after=$1
last_id=$(bosh events --after "${after}" --json | jq -r '.Tables[].Rows[-1].id' | cut -d\  -f 1)
bosh events --after "${after}"
last_last_id=0
for i in {1..1000}; do 
    if [[ ${last_id} == ${last_last_id} ]]; then break; fi
    last_last_id="${last_id}"
    last_id=$(bosh events --after "${after}" --before-id "${last_id}" --json | jq -r '.Tables[].Rows[-1].id' | cut -d\  -f 1)
    bosh events --after "${after}" --before-id "${last_id}"
done
