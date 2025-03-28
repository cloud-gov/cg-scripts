#!/usr/bin/env python3

import os
import boto3
import datetime
import functools
import json
import subprocess

rds_client = boto3.client("rds")
cloudwatch_client = boto3.client("cloudwatch")

PROD_DATABASE_PREFIX = "cg-aws-broker-prod"


@functools.cache
def get_cf_entity_name(entity, guid):
    """
    Retrieves the name of a CF entity from a GUID.
    """
    if not guid:
        return
    cf_json = subprocess.check_output(
        "cf curl /v3/" + entity + "/" + guid,
        universal_newlines=True,
        shell=True,
    )
    cf_data = json.loads(cf_json)
    return cf_data.get("name", "N/A")


def print_all_db_instances_csv_lines():
    rds_response = rds_client.describe_db_instances()
    print_db_instances_csv_lines(rds_response["DBInstances"])
    while "Marker" in rds_response:
        rds_response = rds_client.describe_db_instances(Marker=rds_response["Marker"])
        print_db_instances_csv_lines(rds_response["DBInstances"])


def print_db_instances_csv_lines(instances):
    """
    Prints info about each database as a CSV (comma-separated) line
    """

    for db_instance in instances:
        # Skip databases that aren't brokered in production
        if PROD_DATABASE_PREFIX not in db_instance["DBInstanceIdentifier"]:
            continue

        # Retrieve all of the tags associated with the instance.
        tags = {tag.get("Key"): tag.get("Value") for tag in db_instance["TagList"]}

        org_guid = tags.get("Organization GUID", "")
        org_name = get_cf_entity_name("organizations", org_guid) if org_guid else ""

        space_guid = tags.get("Space GUID", "")
        space_name = get_cf_entity_name("spaces", space_guid) if space_guid else ""

        instance_guid = tags.get("Instance GUID", "")
        instance_name = (
            get_cf_entity_name("service_instances", instance_guid)
            if instance_guid
            else ""
        )

        now = datetime.datetime.now()
        db_identifier = db_instance["DBInstanceIdentifier"]

        free_storage_space_metric = cloudwatch_client.get_metric_statistics(
            Namespace="AWS/RDS",
            MetricName="FreeStorageSpace",
            Dimensions=[
                {
                    "Name": "DBInstanceIdentifier",
                    "Value": db_identifier,
                }
            ],
            Unit="Bytes",
            Statistics=["Maximum"],
            Period=60,
            StartTime=now - datetime.timedelta(minutes=1),
            EndTime=now,
        )
        if free_storage_space_metric["Datapoints"]:
            free_space_bytes = free_storage_space_metric["Datapoints"][0]["Maximum"]
            free_space_gigabytes = free_space_bytes / (10**9)
        else:
            free_space_gigabytes = "Unknown"

        output = "{db_identifer},{engine},{engine_version},{storage_type},{storage_size},{free_space_gigabytes},{org_guid},{space_guid},{instance_guid},{org_name},{space_name},{instance_name},{instance_create_time},{preferred_maintenance_window},{auto_minor_version_upgrade}".format(
            db_identifer=db_instance["DBInstanceIdentifier"],
            engine=db_instance["Engine"],
            engine_version=db_instance["EngineVersion"],
            storage_type=db_instance["StorageType"],
            storage_size=db_instance["AllocatedStorage"],
            free_space_gigabytes=free_space_gigabytes,
            org_guid=org_guid,
            space_guid=space_guid,
            instance_guid=instance_guid,
            org_name=org_name,
            space_name=space_name,
            instance_name=instance_name,
            instance_create_time=db_instance["InstanceCreateTime"],
            preferred_maintenance_window=db_instance["PreferredMaintenanceWindow"],
            auto_minor_version_upgrade=db_instance["AutoMinorVersionUpgrade"],
        )

        print(output)


def print_rds_database_csv_header():
    if os.getenv("NO_HEADER"):
        return
    print(
        "Database ID,Engine,Engine Version,Storage Type,Storage Size (in GB),Free storage (in GB),Organization GUID,Space GUID,Instance GUID,Org,Space,Instance,Created,Maintenance window,Auto minor version upgrade"
    )


def print_rds_database_audit_csv():
    print_rds_database_csv_header()
    print_all_db_instances_csv_lines()


def main():
    print_rds_database_audit_csv()


if __name__ == "__main__":
    main()
