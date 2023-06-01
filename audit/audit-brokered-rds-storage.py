#!/usr/bin/env python3

import boto3

rds_client = boto3.client('rds')

def print_all_db_instances_csv_lines():
    rds_response = rds_client.describe_db_instances()
    print_db_instances_csv_lines(rds_response['DBInstances'])
    while 'Marker' in rds_response:
        rds_response = rds_client.describe_db_instances(Marker=rds_response['Marker'])
        print_db_instances_csv_lines(rds_response['DBInstances'])

def print_db_instances_csv_lines(instances):
    """
    Prints info about each database as a CSV (comma-separated) line
    """

    for db_instance in instances:
        # Retrieve all of the tags associated with the instance.
        tags = { tag.get("Key"): tag.get("Value") for tag in db_instance["TagList"] }

        org_guid = tags.get("Organization GUID", "")
        space_guid = tags.get("Space GUID", "")
        instance_guid = tags.get("Instance GUID", "")

        output = "{db_identifer},{instance_class},{storage_type},{storage_size},{instance_guid},{space_guid},{org_guid}".format(
            db_identifer=db_instance["DBInstanceIdentifier"],
            instance_class=db_instance["DBInstanceClass"],
            storage_type=db_instance["StorageType"],
            storage_size=db_instance["AllocatedStorage"],
            instance_guid=instance_guid,
            space_guid=space_guid,
            org_guid=org_guid,
        )

        print(output)

def print_rds_database_csv_header():
  print("Database ID,Instance Class,Storage Type,Storage Size,Instance GUID,Space GUID,Organization GUID")
  
def print_rds_database_audit_csv():
  print_rds_database_csv_header()
  print_all_db_instances_csv_lines()

def main():
  print_rds_database_audit_csv()

if __name__ == "__main__":
    main()
