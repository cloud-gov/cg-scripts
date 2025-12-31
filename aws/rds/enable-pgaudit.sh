#!/bin/bash


set -eu -o pipefail

#org=cloud-gov-operators
#space=peter.burkholder
#service_instance=mia-django-db-x-psql15

echo "Service Instance: $service_instance in Org: $org, Space: $space"


function reboot_instance() {
  [ $# -ne 2 ] && echo "Function: reboot_instance <db_instance> <attempt>" && exit 1
  local db_instance=$1
  local attempt=$2

  set +e
  aws rds reboot-db-instance \
    --db-instance-identifier "$db_instance"
  status=$?
  set -e

  if [ $status -eq 254 ]; then
    echo "Failed to reboot instance $db_instance status code 254"
    attempt=$((attempt + 1))
    if [ $attempt -gt 5 ]; then
      echo "Exceeded maximum reboot attempts. Exiting."
      exit 1
    fi
    echo "Sleeping 30 seconds and trying again..."
    sleep 30
    reboot_instance "$db_instance" $attempt
  elif [ $status -ne 0 ]; then
    echo "Failed to reboot instance $db_instance with status code $status. Exiting." 
    exit 1
  fi
}

function create_and_associate_parameter_group() {
  [ $# -ne 2 ] && echo "Function: create_parameter_group <current_parameter_group> <db_instance>" && exit 1
  local current_parameter_group=$1
  local db_instance=$2

  family=$(echo "${current_parameter_group}" | awk -F. '{print $NF}')

  echo ============ create new parameter group ===========
  aws rds create-db-parameter-group \
    --db-parameter-group-name "$db_instance" \
    --db-parameter-group-family "$family" \
    --description "Parameter group with pgaudit enabled"

  setup_pgaudit_parameter "$db_instance"

  echo =========== associate new parameter group with instance ===========
  aws rds modify-db-instance \
    --db-instance-identifier "$db_instance" \
    --db-parameter-group-name "$db_instance" \
    --apply-immediately
}


function setup_pgaudit_parameter() {
  [ $# -ne 1 ] && echo "Function: setup_pgaudit <parameter_group>" && exit 1
  local parameter_group=$1

  echo =========== modify pgaudit settings in parameter group ===========
  aws rds modify-db-parameter-group \
    --db-parameter-group-name "$parameter_group" \
    --parameters "ParameterName=shared_preload_libraries,ParameterValue=pgaudit,ApplyMethod=pending-reboot" 
}

# check if parameter group already has pgaudit enabled
function pgaudit_is_enabled() {
  [ $# -ne 1 ] && echo "Function: check_pgaudit_enabled <parameter_group>" && exit 1
  local parameter_group=$1

  pgaudit_value=$(aws rds describe-db-parameters \
    --db-parameter-group-name "$parameter_group" \
    --query "Parameters[?ParameterName=='shared_preload_libraries'].ParameterValue" \
    --output text)

  if [[ "$pgaudit_value" == *pgaudit* ]]; then
    echo "pgaudit_value: >$pgaudit_value< indicates pgaudit is enabled"
    return 0
  else
    echo "pgaudit_value: >$pgaudit_value< indicates pgaudit is NOT enabled"
    return 1
  fi
}


cf target -o $org -s $space > /dev/null
service_instance_guid=$(cf service $service_instance --guid)
echo "Service Instance GUID: $service_instance_guid"

# get ARN
arn=$(aws resourcegroupstaggingapi get-resources \
  --resource-type-filters "rds:db" \
  --tag-filters Key="Instance GUID",Values="$service_instance_guid" \
  | jq -r '.ResourceTagMappingList[].ResourceARN' | grep -v replica  )

# get AWS instancea name from ARN
db_instance=$(echo $arn | awk -F: '{print $NF}')
echo "RDS Instance: $db_instance"

# determine current parameter group
current_parameter_group=$(aws rds describe-db-instances \
  --db-instance-identifier "$db_instance" \
  --query 'DBInstances[0].DBParameterGroups[?DBParameterGroupName!=`default`].DBParameterGroupName' \
  --output text)

echo "Current parameter group: $current_parameter_group"

# Determine whether we need to create a new parameter group or modify existing one
case $current_parameter_group in
  "" )
    echo "No custom parameter group associated with instance. Failing..."
    exit 1
    ;;
  *default* )
    echo "Uses default parameter group $current_parameter_group."
    echo "Creating new parameter group $db_instance and associating it with instance."
    create_and_associate_parameter_group "$current_parameter_group" "$db_instance"
    reboot_instance "$db_instance" 0
    ;;
  *$db_instance* )
    echo "Parameter group already set to $db_instance."
    if pgaudit_is_enabled "$current_parameter_group"; then
      echo "pgaudit is already enabled in parameter group $current_parameter_group. Exiting."
      exit 0
    else
      echo "Enabling pgaudit in parameter group $current_parameter_group."
      setup_pgaudit_parameter "$current_parameter_group"
      reboot_instance "$db_instance" 0
    fi
    exit 0
    ;;
  * )
    echo "Unknown parameter group $current_parameter_group. Failing..."
    exit 1
    ;;
esac    

echo "Well, how did we get here?"
exit 0