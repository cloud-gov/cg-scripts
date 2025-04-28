#!/usr/bin/env python3

import subprocess
import sys
import json
import boto3
import datetime
import functools
import urllib.parse
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
        self.memory_quota = self.get_memory_quota()
        self.memory_usage = self.get_memory_usage()
        self.rds_instances = []
        self.redis_instances = []
        self.es_instances = []
        self.s3_buckets = []
        self.rds_allocation = 0
        self.s3_storage = 0

    def get_data(self):
        cf_json = subprocess.check_output(
            "cf curl /v3/organizations/?names=" + self.name,
            universal_newlines=True,
            shell=True,
        )
        return json.loads(cf_json)["resources"][0]

    def get_memory_quota(self):
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
        print(f"Organization memory quota (GB): {self.memory_quota/1024:.2f}")
        print(f"Organization memory usage (GB): {self.memory_usage/1024:.2f}")
        # FIXME: Some larger orgs would like usage data split out by space
        # not sure how to best do that
        # print(f"Organization spaces: {org.space_names}")

    def report_rds(self, tags_client):
        self.rds_instance_plans = Counter()
        rds_client = boto3.client("rds")

        self.get_rds_instances(tags_client)
        for rds in self.rds_instances:
            rds.get_db_instance(rds_client)
            self.rds_instance_plans[rds.service_plan_name] += 1
            self.rds_allocation += rds.allocated_storage

        print("RDS:")
        print(f" RDS allocation (GB): {self.rds_allocation}")
        print(f" RDS Plans")
        for key, value in sorted(self.rds_instance_plans.items()):
            print(f"  {key}: {value}")


    def report_s3(self, tags_client):
        print("S3")
        self.s3_total_storage = 0
        cloudwatch_client = boto3.client("cloudwatch")

        self.get_s3_buckets(tags_client)
        for s3 in self.s3_buckets:
            s3.get_s3_usage(cloudwatch_client)
            self.s3_total_storage += s3.s3_usage
        print(f" S3 Total Usage (GB): {self.s3_total_storage/(1024*1024*1024):.2f}")


    def report_redis(self, tags_client):
        print("Redis:")
        self.redis_instance_plans = Counter()

        self.get_redis_instances(tags_client)
        for redis in self.redis_instances:
            self.redis_instance_plans[redis.service_plan_name] += 1
        print(f" Redis Plans")
        for key, value in sorted(self.redis_instance_plans.items()):
            print(f"  {key}: {value}")


    def report_es(self, tags_client):
        print("ES")
        es_client = boto3.client("es")
        self.es_instance_plans = Counter()
        self.es_volume_storage = 0

        self.get_es_instances(tags_client)
        for es in self.es_instances:
            es.get_es_instance(es_client)
            self.es_instance_plans[es.service_plan_name] += 1
            self.es_volume_storage += es.volume_size
        print(f" ES volume storage (GB): {self.es_volume_storage}")
        print(f" ES Plans")

        for key, value in sorted(self.es_instance_plans.items()):
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
        self.org_names = orgs

        self.resource_tags_client = boto3.client("resourcegroupstaggingapi")

        self.memory_quota = 0
        self.memory_usage = 0
        self.rds_total_allocation = 0
        self.s3_total_storage = 0
        self.es_total_volume_storage = 0

        self.rds_total_instance_plans = Counter()
        self.redis_total_instance_plans = Counter()
        self.es_total_instance_plans = Counter()
        self.worksheet_file = None

    def report_orgs(self):
        for org_name in self.org_names:
            # urlencode name to ensure that names with possible URL escape 
            # characters (e.g. +) will be handled properly when querying the CF API
            org_name = urllib.parse.quote_plus(org_name)
            org = Organization(name=org_name)    
            print("-----------------------------")
            org.report_memory()
            self.memory_quota += org.memory_quota
            self.memory_usage += org.memory_usage

            org.report_rds(self.resource_tags_client)
            for key, value in org.rds_instance_plans.items():
                self.rds_total_instance_plans[key] += value
            self.rds_total_allocation += org.rds_allocation

            org.report_s3(self.resource_tags_client)
            self.s3_total_storage += org.s3_total_storage

            org.report_redis(self.resource_tags_client)
            for key, value in org.redis_instance_plans.items():
                self.redis_total_instance_plans[key] += value

            org.report_es(self.resource_tags_client)
            for key, value in org.es_instance_plans.items():
                self.es_total_instance_plans[key] += value
            self.es_total_volume_storage += org.es_volume_storage
    
    def report_summary(self):
        print("=============================")
        print(f"Account Total Mem Quota (GB): {self.memory_quota/1024:.0f}")
        print(f"Account Total Mem Usage (GB): {self.memory_usage/1024:.0f}")
        print(f"Account RDS Total Alloc (GB): {self.rds_total_allocation:.0f}")
        print(f"Account RDS Plans")
        for key, value in sorted(self.rds_total_instance_plans.items()):
            print(f"  {key}: {value}")
        print(f"Account S3 Total Usage (GB): {self.s3_total_storage/(1024*1024*1024):.0f}")
        print(f"Account Redis Plans")
        for key, value in sorted(self.redis_total_instance_plans.items()):
            print(f"  {key}: {value}")
        print(f"Account ES Plans")
        for key, value in sorted(self.es_total_instance_plans.items()):
            print(f"  {key}: {value}")

    def generate_cost_estimate(self):

        from openpyxl import load_workbook
        self.worksheet_file = "cloud-gov-cost-estimator.xlsx"
        workbook = load_workbook(filename=self.worksheet_file)
        sheet = workbook.active
        sheet["A1"] = "Full Name"
        workbook.save(filename=self.worksheet_file)

def main():
    if len(sys.argv) == 1:
        print("Provide an org name")
        sys.exit(-1)

    test_authenticated("cf")
    test_authenticated("aws")

    org_names = sys.argv[1:]

    acct = Account(orgs=org_names)
    acct.report_orgs()
    if len(org_names) > 1:
        acct.report_summary()
    acct.generate_cost_estimate()


if __name__ == "__main__":
    main()
