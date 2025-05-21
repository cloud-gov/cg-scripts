#!/bin/bash

function usage {
  echo -e "
  ./$( basename "$0" ) <bucket_name> <date> <load_balancer_name> <zulu_time> <output directory>

  Download load balancer logs from S3 for the given date, load balancer, and timestamp (in Zulu time).

    - Date in YYYY/MM/DD format, e.g. 2024/01/03
    - Timestamp should be in YYYYMMDDTHHMM format, e.g. 20240103T1500 (January 3, 2024 at 3 PM Zulu time)

  Environment variable AWS_DEFAULT_REGION can be used to change the region for the script.

  Examples:

    ./$( basename "$0" ) example-elb-logs 2024/01/03 load-balancer-1 20240103T1500 ~/Downloads
  "
}

BUCKET=$1
DATE=$2
LB_NAME=$3
TIME=$4
OUTPUT_DIR=$5

if [ "$#" -ne 5 ]; then
  usage
  exit 1
fi

REGION=${AWS_DEFAULT_REGION:-us-gov-west-1}
ACCOUNT_ID=$(aws sts get-caller-identity | jq -r '.Account')

LOAD_BALANCER_ARN=$(aws elbv2 describe-load-balancers --names "$LB_NAME" | jq -r '.LoadBalancers[0].LoadBalancerArn')
LOAD_BALANCER_ID=$(echo "$LOAD_BALANCER_ARN" | cut -d '/' -f 3,4 | sed 's/\//./')

PREFIX="production/AWSLogs/$ACCOUNT_ID/elasticloadbalancing/$REGION/$DATE/${ACCOUNT_ID}_elasticloadbalancing_${REGION}_app.${LOAD_BALANCER_ID}_$TIME"

for key in $(aws s3api list-objects-v2 --bucket "$BUCKET" --prefix "$PREFIX" | jq -r '.Contents[].Key'); do
  aws s3 cp "s3://$BUCKET/$key" "$OUTPUT_DIR"
done
