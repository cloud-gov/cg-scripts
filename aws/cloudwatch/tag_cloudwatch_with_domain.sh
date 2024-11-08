REGION=$(aws configure get region)
log_groups=$(aws logs describe-log-groups --region $REGION --query "logGroups[?starts_with(logGroupName, '/aws/OpenSearchService/domains/')].logGroupName" --output text)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

for instance in $log_groups; do
    TAG=${instance#/aws/OpenSearchService/domains/}
    TAG=${TAG%/*}
    ARN="arn:aws-us-gov:es:${REGION}:${ACCOUNT_ID}:domain/${TAG}"
    DOMAIN_TAGS=$(aws opensearch list-tags --arn ${ARN} --query "TagList" --output json)
    TAGS_STRING=$(echo "$DOMAIN_TAGS" | jq -r '.[] | "\(.Key)=\(.Value)"' | paste -sd ',' -)
    TAGS_STRING=$(echo "$TAGS_STRING" | sed 's/ //g')
    if [ -z "$DOMAIN_TAGS" ]; then
        echo "invalid tags for ${instance}, does it exist?"
    else
        echo "Success on ${instance}"
        aws logs tag-log-group --log-group-name "${instance}" --tags "$TAGS_STRING"
    fi
done

