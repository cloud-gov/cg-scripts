#!/bin/sh

# WARNING:  DESTRUCTIVE OPERATION

# Recursively empties the contents of an S3 bucket.  You must be in the org and
# space of the bucket you would like to empty.

# This operation may take some time depending on how many objects are in the
# bucket.  If there are a large number of objects it may be better to do the
# following:

# 1. Create a service key to get the bucket credentials
# 2. Find the bucket in the AWS console
# 3. Create a lifecycle policy to clear the bucket contents

# Requires the cf CLI, awscli, and jq.

set -e -x

if [ "$#" -ne 1 ]; then
  echo
  echo "Usage:"
  echo "   ./empty-s3-bucket.sh <service instance name>"
  echo

  exit 1
fi

# Create a service key and retrieve the credentials from it to use with awscli.
SERVICE_INSTANCE_NAME="$1"
KEY_NAME="cg-operator-empty-s3-bucket-key"

# If the service key already exists, the cf CLI will ignore it and carry on
# without an error.
cf create-service-key "$SERVICE_INSTANCE_NAME" $KEY_NAME
S3_CREDENTIALS=$(cf service-key "$SERVICE_INSTANCE_NAME" $KEY_NAME | tail -n +2)

export AWS_ACCESS_KEY_ID
AWS_ACCESS_KEY_ID=$(echo "$S3_CREDENTIALS" | jq -r '.credentials.access_key_id')
export AWS_SECRET_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=$(echo "$S3_CREDENTIALS" | jq -r '.credentials.secret_access_key')
export BUCKET_NAME
BUCKET_NAME=$(echo "$S3_CREDENTIALS" | jq -r '.credentials.bucket')
export AWS_DEFAULT_REGION
AWS_DEFAULT_REGION=$(echo "$S3_CREDENTIALS" | jq -r '.credentials.region')

# it takes time for the new creds to propagate in AWS so
# we have to while here for abit or this script fails almost every time.
x=0
set +e
while [ $x -lt 5 ]; do
  aws s3 ls "s3://$BUCKET_NAME" > /dev/null 2>&1
  ready=$?
  if [ $ready -ne 0 ]; then
     x=$(( x + 1 ))
     echo "waiting for credentials to be ready in aws..."
     sleep 2;
  else
    break
  fi
done
set -e

# Empty the bucket.
aws s3 rm "s3://$BUCKET_NAME" --recursive

# Remove the service key.
cf delete-service-key "$SERVICE_INSTANCE_NAME" $KEY_NAME -f
