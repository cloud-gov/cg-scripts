#!/bin/sh

# WARNING:  DESTRUCTIVE OPERATION

# Recursively empties the contents of an S3 bucket.  You must be in the org and
# space of the bucket you would like to empty.

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
KEY_NAME="$SERVICE_INSTANCE_NAME-key"

# If the service key already exists, the cf CLI will ignore it and carry on
# without an error.
cf create-service-key $SERVICE_INSTANCE_NAME $KEY_NAME
S3_CREDENTIALS=$(cf service-key $SERVICE_INSTANCE_NAME $KEY_NAME | tail -n +2)

export AWS_ACCESS_KEY_ID=$(echo $S3_CREDENTIALS | jq -r '.access_key_id')
export AWS_SECRET_ACCESS_KEY=$(echo $S3_CREDENTIALS | jq -r '.secret_access_key')
export BUCKET_NAME=$(echo $S3_CREDENTIALS | jq -r '.bucket')
export AWS_DEFAULT_REGION=$(echo $S3_CREDENTIALS | jq -r '.region')

# Empty the bucket.
aws s3 rm -r * s3://$BUCKET_NAME

# Remove the service key.
cf delete-service-key $SERVICE_INSTANCE_NAME $KEY_NAME -f
