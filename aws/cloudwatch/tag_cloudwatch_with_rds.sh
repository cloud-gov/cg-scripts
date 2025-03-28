#!/bin/bash

log_groups=$(aws logs describe-log-groups --region "$AWS_REGION" --query "logGroups[?starts_with(logGroupName, '/aws/rds/instance/')].logGroupName" --output text)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

for instance in $log_groups; do
    TAG=${instance#/aws/rds/instance/}
    TAG=${TAG%/*}
    ARN="arn:aws-us-gov:rds:${AWS_REGION}:${ACCOUNT_ID}:db:${TAG}"

    if ! aws rds describe-db-instances --db-instance-identifier "$ARN" > /dev/null; then
        echo "no database instance for $ARN" >&2
        continue
    fi

    RDS_TAGS=$(aws rds list-tags-for-resource --resource-name "$ARN" --query "TagList" --output json)
    TAGS_STRING=$(echo "$RDS_TAGS" | jq -r '.[] | "\(.Key)=\(.Value)"' | paste -sd ',' -)
    TAGS_STRING=${TAGS_STRING// /}

    if [ -z "$RDS_TAGS" ]; then
        echo "invalid tags for ${instance}, does it exist?"
    else
        aws logs tag-log-group --log-group-name "${instance}" --tags "$TAGS_STRING"
        echo "Success on ${instance}"
    fi
done

