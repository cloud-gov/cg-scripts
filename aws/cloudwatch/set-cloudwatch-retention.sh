#!/bin/bash

RETENTION_IN_DAYS=1096 # 3 years, minimum value that exceeds 30 months M-21-31 requirement

for log_group_name in $(aws logs describe-log-groups | jq -r '.logGroups[] | select(.retentionInDays == null) | .logGroupName'); do
  aws logs put-retention-policy --log-group-name "$log_group_name" --retention-in-days $RETENTION_IN_DAYS
  echo "set retention policy for $log_group_name to $RETENTION_IN_DAYS days"
done
