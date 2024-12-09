#!/bin/bash

# Disable AWS pager so output goes straight to console
export AWS_PAGER=''

for domain_name in $(aws opensearch list-domain-names --output json | jq -r '.DomainNames[].DomainName')
do
    aws opensearch describe-domain-config --domain-name "$domain_name" --output table
done
