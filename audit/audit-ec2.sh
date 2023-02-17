#!/bin/bash

# Disable AWS pager so output goes straight to console
export AWS_PAGER=''

aws ec2 describe-instances --output table
aws ec2 describe-volumes --output table
aws ec2 describe-security-groups --output table
aws ec2 describe-network-acls --output table
aws ec2 describe-subnets --output table
aws ec2 describe-route-tables --output table
aws ec2 describe-nat-gateways --output table
aws ec2 describe-vpc-peering-connections --output table
aws ec2 describe-vpc-endpoints --output table
aws ec2 describe-vpc-endpoint-services --output table
aws ec2 describe-vpc-endpoint-service-configurations --output table

for service_id in $(aws ec2 describe-vpc-endpoint-service-configurations  --output json | jq -r '.ServiceConfigurations[].ServiceId'); do
  aws ec2 describe-vpc-endpoint-service-permissions --service-id "$service_id" --output table
done

aws ec2 describe-flow-logs --output table