#!/bin/bash

echo "cert,expiry,ca,ca_expiry,new_expiry" >> results.csv

for certn in $(cat cert_list.txt)
do
  echo renewing cert $certn
  expiry=$(credhub curl -p "/api/v1/certificates?name=$certn" | jq -r '.certificates[0].versions[0].expiry_date')
  ca=$(credhub curl -p "/api/v1/certificates?name=$certn" | jq -r '.certificates[0].signed_by')
  ca_expiry=$(credhub curl -p "/api/v1/certificates?name=$ca" | jq -r '.certificates[0].versions[0].expiry_date')

  credhub regenerate -n $certn
  new_expiry=$(credhub curl -p "/api/v1/certificates?name=$certn" | jq -r '.certificates[0].versions[0].expiry_date')

  echo "$certn,$expiry,$ca,$ca_expiry,$new_expiry" >> results.csv
done
