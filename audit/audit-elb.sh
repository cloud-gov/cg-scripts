#!/bin/bash

# Disable AWS pager so output goes straight to console
export AWS_PAGER=''

aws elbv2 describe-load-balancers --output table

for load_balancer_arn in $(aws elbv2 describe-load-balancers --output json | jq -r '.LoadBalancers[].LoadBalancerArn');
do
  aws elbv2 describe-load-balancer-attributes --load-balancer-arn "$load_balancer_arn" --output table
  aws elbv2 describe-listeners --load-balancer-arn "$load_balancer_arn" --output table
  aws elbv2 describe-tags --resource-arns "$load_balancer_arn" --output table
  aws elbv2 describe-target-groups --load-balancer-arn "$load_balancer_arn" --output table

  for target_group_arn in $(aws elbv2 describe-target-groups --load-balancer-arn "$load_balancer_arn" --output json | jq -r '.TargetGroups[].TargetGroupArn');
  do
    aws elbv2 describe-target-health --target-group-arn "$target_group_arn" --output table
  done
done
