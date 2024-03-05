#!/usr/bin/env bash

INPUT_FILE="$1"
if [[ -z "$INPUT_FILE" ]]; then
  echo "Input file name must be specified as first argument to script."
  exit 1
fi

while read -r line; do
  IFS=',' read -r -a array <<< "$line"
  ORG_NAME="${array[0]}"
  SPACE_NAME="${array[1]}"
  DB_NAME="${array[2]}"
  MAINTENANCE_WINDOW="${array[3]}"

  cf target -o "$ORG_NAME" -s "$SPACE_NAME" > /dev/null

  DB_GUID=$(cf service "$DB_NAME" --guid)
  DB_ARN=$(aws resourcegroupstaggingapi get-resources \
    --resource-type-filters "rds:db" \
    --tag-filters Key="Instance GUID",Values="$DB_GUID" \
    | jq -r '.ResourceTagMappingList[].ResourceARN')

  echo "org: $ORG_NAME, space: $SPACE_NAME, database: $DB_NAME"
  printf "database GUID: %s, database ARN: %s\n" "$DB_GUID" "$DB_ARN"

  DB_INFO=$(aws rds describe-db-instances --db-instance-identifier "$DB_ARN")
  DB_INSTANCE_TYPE=$(echo "$DB_INFO" | jq -r '.DBInstances[0].DBInstanceClass')
  CUR_MAINTENANCE_WINDOW=$(echo "$DB_INFO" | jq -r '.DBInstances[0].PreferredMaintenanceWindow')

  printf "instance type for %s is %s\n" "$DB_NAME" "$DB_INSTANCE_TYPE"

  if [ "$MAINTENANCE_WINDOW" != "$CUR_MAINTENANCE_WINDOW" ]; then
    printf "expected maintenance window %s does not match current maintenance window %s\n" "$MAINTENANCE_WINDOW" "$CUR_MAINTENANCE_WINDOW"
  fi

  printf "\n"
done < "$INPUT_FILE"
