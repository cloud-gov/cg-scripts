#!/bin/bash

if [ -z "$1" ]; then
  echo
  echo "Usage:"
  echo "    $ ./bosh-audit.sh <after-date>"
  echo
  exit 1;
fi

after="$1"
last_row=$(bosh events --after "${after}" --json | tee jq -r '.Tables[].Rows[-1].id' - )
last_id=$(cut -d\  -f 1 < "${last_row}")
last_last_id=0
for i in {1..1000}; do 
    if [[ ${last_id} == ${last_last_id} ]]; then break; fi
    last_last_id="${last_id}"
    last_row=$(bosh events --after "${after}" --before-id "${last_id}" --json | tee jq -r '.Tables[].Rows[-1].id' - )
    last_id=$(cut -d\  -f 1 < "${last_row}")
done
