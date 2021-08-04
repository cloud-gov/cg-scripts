#!/bin/bash -ex

echo $CERTBOT_VALIDATION > ./$CERTBOT_TOKEN

aws s3 cp --sse AES256 $CERTBOT_TOKEN s3://$CERTBOT_BUCKET_NAME/.well-known/acme-challenge/$CERTBOT_TOKEN

sleep 5
