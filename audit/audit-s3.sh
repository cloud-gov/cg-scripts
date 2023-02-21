#!/bin/bash

# Disable AWS pager so output goes straight to console
export AWS_PAGER=''

ACCOUNT_ID=$(aws sts get-caller-identity --output json | jq -r '.Account')
aws s3control get-public-access-block --account-id "$ACCOUNT_ID" --output table
aws s3api list-buckets --output table

for bucket in $(aws s3api list-buckets --output json | jq -r '.Buckets[].Name'); do
  aws s3api get-bucket-acl --bucket "$bucket" --output table
  aws s3api get-bucket-policy --bucket "$bucket" --output table
  aws s3api get-bucket-policy-status --bucket "$bucket" --output table
  aws s3api get-public-access-block --bucket "$bucket" --output table
  aws s3api get-bucket-logging --bucket "$bucket" --output table
  aws s3api get-bucket-versioning --bucket "$bucket" --output table
  aws s3api get-bucket-encryption --bucket "$bucket" --output table
  aws s3api get-bucket-replication --bucket "$bucket" --output table
done
