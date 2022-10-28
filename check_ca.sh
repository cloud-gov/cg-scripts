#!/bin/bash

for certn in $(cat cert_list.txt)
do
  ca=$(credhub curl -p "/api/v1/certificates?name=$certn" | jq -r '.certificates[0].signed_by')
  echo "$certn: $ca"
done
