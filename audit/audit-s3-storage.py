#!/usr/bin/env python3

import os
import boto3
from botocore.exceptions import ClientError
import datetime
import functools
import json
import subprocess

s3_client = boto3.client("s3")
cloudwatch_client = boto3.client("cloudwatch")

PROD_S3_PREFIX = "cg-"
# S3 ID,Storage Size,Organization GUID,Space GUID,Org,Space
# cg-018c0680-39b1-4a7f-af37-5a150aa715b3,507.588725 MB,50807f74-fbc6-4a86-a8fb-80d42ac6ad3e,a1e19bd4-5066-40a7-8d53-fc9644c27e8e,gsa-18f-federalist,production


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

def filter_bucket_list_by_org(bucket_list, org_guid):
    '''
    returns only the buckets that have been tagged
    with Name: "Organization ID"
    and Value: org_guid
    '''
    return ['cg-018c0680-39b1-4a7f-af37-5a150aa715b3'] # gsa-18f-federalist-bucket

def print_all_s3_instances_csv_lines(org_guid=None):
    buckets = s3_client.list_buckets()
    bucket_list=[bucket['Name'] for bucket in buckets['Buckets']]
    if org_guid:
        bucket_list = filter_bucket_list_by_org(org_guid)
    print_s3_instances_csv_lines(bucket_list)


def print_s3_instances_csv_lines(instances):
    """
    Prints info about each s3 bucket as a CSV (comma-separated) line
    """

    for s3_instance in instances:
        # Skip databases that aren't brokered in production
        if PROD_S3_PREFIX not in s3_instance:
            continue

        tags = {}
        # Retrieve all of the tags associated with the instance.
        try:
            s3_instance_tag_list=s3_client.get_bucket_tagging(Bucket=s3_instance)
            tag_list=s3_instance_tag_list.get('TagSet',[])
            tags = {tag.get("Key"): tag.get("Value") for tag in tag_list}
        except ClientError as e:
            tags={}
        # Was Organization GUID for RDS
        org_guid = tags.get("Organization ID", "")
        if org_guid == "":
            org_guid = tags.get("Organization GUID", "")
            if org_guid == "organizationGuid":
                org_guid = tags.get("organizationGuid","")
        org_name = get_cf_entity_name("organizations", org_guid) if org_guid else ""

        # Was Space GUID for RDS
        space_guid = tags.get("Space ID", "")
        if space_guid == "":
            space_guid = tags.get("Space GUID", "")
            if space_guid == "":
                space_guid = tags.get("spaceGuid", "")
        space_name = get_cf_entity_name("spaces", space_guid) if space_guid else ""

        now = datetime.datetime.now()
        s3_space_used = cloudwatch_client.get_metric_statistics(
            Namespace="AWS/S3",
            MetricName="BucketSizeBytes",
            Dimensions=[
                {
                    "Name":"BucketName",
                    "Value":s3_instance,
                },
                {
                    "Name":"StorageType",
                    "Value":"StandardStorage",
                }
            ],
            Statistics=["Average"],
            Period=86400,
            StartTime=now - datetime.timedelta(days=1),
            EndTime=now,
            Unit="Bytes",
        )

        if s3_space_used["Datapoints"]:
            used_space_bytes = s3_space_used["Datapoints"][0]["Average"]
            used_space_gigabytes = used_space_bytes / (10**9)
            if used_space_gigabytes < 1:
                used_space = str(used_space_bytes / (10**6)) + " MB"
            else:
                used_space = str(used_space_gigabytes) + " GB"
        else:
            used_space = "Might be Empty"


        output = "{s3_name},{storage_size},{org_guid},{space_guid},{org_name},{space_name}".format(
            s3_name=s3_instance,
            storage_size=used_space,
            org_guid=org_guid,
            space_guid=space_guid,
            org_name=org_name,
            space_name=space_name,
        )

        print(output)


def print_s3_database_csv_header():
    if os.getenv("NO_HEADER"):
        return
    print(
        "S3 ID,Storage Size,Organization GUID,Space GUID,Org,Space"
    )


def print_s3_database_audit_csv():
    print_s3_database_csv_header()
    print_all_s3_instances_csv_lines('asdflkj')


def main():
    print("Make sure you are logged into cloudfoundry")
    print_s3_database_audit_csv()


if __name__ == "__main__":
    main()