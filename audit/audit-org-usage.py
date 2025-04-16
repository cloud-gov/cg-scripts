#!/usr/bin/env python3

import subprocess
import sys
import json
import boto3
import datetime
import functools
from collections import Counter


class AWSResource:
    def __init__(self, arn, tags):
        self.arn = arn
        self.tags = tags
        if ":" in arn:
            self.instance_id = arn.split(":")[-1]
        else:
            self.instance_id = "Unknown"


class AWSNotS3(AWSResource):
    def __init__(self, arn, tags):
        super().__init__(arn, tags)
        self.instance_guid = [
            tag["Value"] for tag in tags if tag["Key"] == "Instance GUID"
        ][0]
        self.space_guid = [tag["Value"] for tag in tags if tag["Key"] == "Space GUID"][
            0
        ]
        try:
            self.space_name = [
                tag["Value"] for tag in tags if tag["Key"] == "Space name"
            ][0]
        except:
            self.space_name = self.get_cf_entity_name("spaces", self.space_guid)

        # FIXME: Maybe we shouldn't trust the plan name in the tag, but it's faster
        try:
            self.service_plan_name = [
                tag["Value"] for tag in tags if tag["Key"] == "Service plan name"
            ][0]
        except:
            try:
                self.service_plan_name = self.get_instance_plan_name(self.instance_guid)
            except:
                self.service_plan_name = "Not Found"

        # NOTE: 'instance_name' could change with `cf rename-service`
        try:
            self.instance_name = [
                tag["Value"] for tag in tags if tag["Key"] == "Instance name"
            ][0]
        except:
            self.instance_name = "Not Found"

    @functools.cache
    def get_cf_entity_name(self, entity, guid):
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

    def get_instance_plan_name(self, instance_guid):
        cf_json = subprocess.check_output(
            "cf curl /v3/service_instances/"
            + instance_guid
            + "/?fields[service_plan]=name",
            universal_newlines=True,
            shell=True,
        )
        cf_data = json.loads(cf_json)
        return cf_data.get("included", "N/A")["service_plans"][0]["name"]


class Rds(AWSNotS3):
    def __init__(self, arn, tags):
        super().__init__(arn, tags)

    def get_db_instance(self, client):
        response = client.describe_db_instances(DBInstanceIdentifier=self.arn)
        instance_info = response["DBInstances"][0]
        self.allocated_storage = instance_info["AllocatedStorage"]


class Redis(AWSNotS3):
    def __init__(self, arn, tags):
        super().__init__(arn, tags)


class Es(AWSNotS3):
    def __init__(self, arn, tags):
        super().__init__(arn, tags)

    def get_es_instance(self, client):
        es_domain_name = self.arn.split("/")[1]
        response = client.describe_elasticsearch_domain(DomainName=es_domain_name)
        domain_status = response["DomainStatus"]
        ebs_options = domain_status.get("EBSOptions", {})
        self.volume_size = ebs_options.get("VolumeSize", 0)


class S3(AWSResource):
    def __init__(self, arn, tags):
        super().__init__(arn, tags)
        self.bucket_name = self.instance_id

    def get_s3_usage(self, client):
        now = datetime.datetime.now()
        response = client.get_metric_statistics(
            Namespace="AWS/S3",
            MetricName="BucketSizeBytes",
            Dimensions=[
                {"Name": "BucketName", "Value": self.bucket_name},
                {
                    "Name": "StorageType",
                    "Value": "StandardStorage",
                },
            ],
            Statistics=["Average"],
            Period=86400,
            StartTime=now - datetime.timedelta(days=1),
            EndTime=now,
            Unit="Bytes",
        )
        self.s3_usage = 0
        datapoints = response["Datapoints"]
        if len(datapoints) > 0:
            self.s3_usage = datapoints[0]["Average"]


class Organization:
    def __init__(self, name):
        self.name = name
        self.data = self.get_data()
        self.guid = self.data["guid"]
        self.quota_guid = self.data["relationships"]["quota"]["data"]["guid"]
        self.rds_instances = []
        self.redis_instances = []
        self.es_instances = []
        self.s3_buckets = []

    def get_data(self):
        cf_json = subprocess.check_output(
            "cf curl /v3/organizations/?names=" + self.name,
            universal_newlines=True,
            shell=True,
        )
        return json.loads(cf_json)["resources"][0]

    def get_quota_memory(self):
        cf_json = subprocess.check_output(
            "cf curl /v3/organization_quotas/" + self.quota_guid,
            universal_newlines=True,
            shell=True,
        )
        return json.loads(cf_json)["apps"]["total_memory_in_mb"]

    def get_memory_usage(self):
        cf_json = subprocess.check_output(
            "cf curl /v3/organizations/" + self.guid + "/usage_summary",
            universal_newlines=True,
            shell=True,
        )
        return json.loads(cf_json)["usage_summary"]["memory_in_mb"]

    def get_aws_instances(self, client, resource_type):
        resource_type_map = {
            "rds": "rds:db",
            "redis": "elasticache:replicationgroup",
            "es": "es:domain",
        }
        resource_type_filter = [resource_type_map[resource_type]]
        tag_key = "Organization GUID"
        tag_value = self.guid
        response = client.get_resources(
            TagFilters=[{"Key": tag_key, "Values": [tag_value]}],
            ResourceTypeFilters=resource_type_filter,
        )
        return response

    def get_rds_instances(self, client):
        response = self.get_aws_instances(client, "rds")
        for resource in response["ResourceTagMappingList"]:
            rds = Rds(resource["ResourceARN"], resource["Tags"])
            self.rds_instances.append(rds)

    def get_redis_instances(self, client):
        response = self.get_aws_instances(client, "redis")
        for resource in response["ResourceTagMappingList"]:
            redis = Redis(resource["ResourceARN"], resource["Tags"])
            self.redis_instances.append(redis)

    def get_es_instances(self, client):
        response = self.get_aws_instances(client, "es")
        for resource in response["ResourceTagMappingList"]:
            es = Es(resource["ResourceARN"], resource["Tags"])
            self.es_instances.append(es)

    def get_s3_buckets(self, client):
        tag_value = self.guid
        for key_value in ["Organization GUID", "Organization ID", "organizationGuid"]:
            response = client.get_resources(
                TagFilters=[{"Key": key_value, "Values": [tag_value]}],
                ResourceTypeFilters=["s3:bucket"],
            )
            for resource in response["ResourceTagMappingList"]:
                s3 = S3(resource["ResourceARN"], resource["Tags"])
                self.s3_buckets.append(s3)

    def report_memory(self):
        print(f"Organization name: {self.name}")
        print(f"Organization GUID: {self.guid}")
        print(f"Organization memory quota (GB): {self.get_quota_memory()/1024:.2f}")
        print(f"Organization memory usage (GB): {self.get_memory_usage()/1024:.2f}")
        # FIXME: Some larger orgs would like usage data split out by space
        # not sure how to best do that
        # print(f"Organization spaces: {org.space_names}")

    def report_rds(self, tags_client):
        print("RDS:")
        rds_instance_plans = Counter()
        rds_allocation = 0
        rds_client = boto3.client("rds")

        self.get_rds_instances(tags_client)
        for rds in self.rds_instances:
            rds.get_db_instance(rds_client)
            rds_instance_plans[rds.service_plan_name] += 1
            rds_allocation += rds.allocated_storage
        print(f" RDS allocation (GB): {rds_allocation}")
        print(f" RDS Plans")
        for key, value in sorted(rds_instance_plans.items()):
            print(f"  {key}: {value}")


    def report_s3(self, tags_client):
        print("S3")
        s3_total_storage = 0
        cloudwatch_client = boto3.client("cloudwatch")

        self.get_s3_buckets(tags_client)
        for s3 in self.s3_buckets:
            s3.get_s3_usage(cloudwatch_client)
            s3_total_storage += s3.s3_usage
        print(f" S3 Total Usage (GB): {s3_total_storage/(1024*1024*1024):.2f}")


    def report_redis(self, tags_client):
        print("Redis:")
        redis_instance_plans = Counter()

        self.get_redis_instances(tags_client)
        for redis in self.redis_instances:
            redis_instance_plans[redis.service_plan_name] += 1
        print(f" Redis Plans")
        for key, value in sorted(redis_instance_plans.items()):
            print(f"  {key}: {value}")


    def report_es(self, tags_client):
        print("ES")
        es_client = boto3.client("es")
        es_instance_plans = Counter()
        es_volume_storage = 0

        self.get_es_instances(tags_client)
        for es in self.es_instances:
            es.get_es_instance(es_client)
            es_instance_plans[es.service_plan_name] += 1
            es_volume_storage += es.volume_size
        print(f" ES volume storage (GB): {es_volume_storage}")
        print(f" ES Plans")

        for key, value in sorted(es_instance_plans.items()):
            print(f"  {key}: {value}")


def test_authenticated(service):
    """
    Try CF and AWS commands to ensure we're logged in to everything
    """
    if service == "aws":
        cmd = "aws sts get-caller-identity"
    elif service == "cf":
        cmd = "cf oauth-token"
    else:
        raise ValueError("Invalid argument: must by 'cf' or 'aws'")

    try:
        result = subprocess.run(
            cmd.split(" "),
            check=True,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as e:
        print(
            f'Error: Command "{cmd}" failed, are you sure you\'re authenticated?',
            file=sys.stderr,
        )
        sys.exit(1)  # Exit with non-zero status cod







class Account:
    def __init__(self, orgs):
        self.orgs = orgs

    def report_memory(org):
        print(f"Organization name: {org.name}")
        print(f"Organization GUID: {org.guid}")
        print(f"Organization memory quota (GB): {org.get_quota_memory()/1024:.2f}")
        print(f"Organization memory usage (GB): {org.get_memory_usage()/1024:.2f}")
    # FIXME: Some larger orgs would like usage data split out by space
    # not sure how to best do that
    # print(f"Organization spaces: {org.space_names}")




def main():
    if len(sys.argv) == 1:
        print("Provide an org name")
        sys.exit(-1)

    org_name = sys.argv[1]
    org = Organization(name=org_name)    
    test_authenticated("cf")
    test_authenticated("aws")


#    org_names = sys.argv[1:]
#    acct = Account(orgs=org_names)
#    acct.report_memory()

    resource_tags_client = boto3.client("resourcegroupstaggingapi")

    org.report_memory()
    org.report_rds(resource_tags_client)
    org.report_s3(resource_tags_client)
    org.report_redis(resource_tags_client)
    org.report_es(resource_tags_client)


if __name__ == "__main__":
    main()
