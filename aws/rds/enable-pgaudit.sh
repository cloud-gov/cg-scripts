#!/bin/bash

set -eu -o pipefail

#org=epa-spds
#space=test
#service_instance=spds-db

org=cloud-gov-operators
space=peter.burkholder
service_instance=mia-django-db-x-psql15

echo "Service Instance: $service_instance in Org: $org, Space: $space"

cf target -o $org -s $space > /dev/null
service_instance_guid=$(cf service $service_instance --guid)
echo "Service Instance GUID: $service_instance_guid"

# get ARN
arn=$(aws resourcegroupstaggingapi get-resources \
  --resource-type-filters "rds:db" \
  --tag-filters Key="Instance GUID",Values="$service_instance_guid" \
  | jq -r '.ResourceTagMappingList[].ResourceARN' | grep -v replica  )

# get AWS instancea name from ARN
instance=$(echo $arn | awk -F: '{print $NF}')
echo "RDS Instance: $instance"

# determine current parameter group
current_parameter_group=$(aws rds describe-db-instances \
  --db-instance-identifier $instance \
  --query 'DBInstances[0].DBParameterGroups[?DBParameterGroupName!=`default`].DBParameterGroupName' \
  --output text)

echo "Current parameter group: $current_parameter_group"

# Determine whether we need to create a new parameter group or modify existing one
case $current_parameter_group in
  "" )
    echo "No custom parameter group associated with instance. Exiting."
    exit 0
    ;;
  *default* )
    echo "Using default parameter group $current_parameter_group. Exiting."
    exit 0
    ;;
  *$service_instance* )
    echo "Parameter group already set to $service_instance_guid. Exiting."
    exit 0
    ;;
  * )
    echo "Unknown parameter group $current_parameter_group. Exiting."
    exit 0
    ;;
esac    


#    aws rds modify-db-instance \
#      --db-instance-identifier $instance \
#      --db-parameter-group-name $service_instance_guid \
#      --apply-immediately
