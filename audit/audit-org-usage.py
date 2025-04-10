#!/usr/bin/env python3

import subprocess
import sys
import json
import boto3
import datetime
import functools
from collections import Counter


tags_client = boto3.client('resourcegroupstaggingapi')
rds_client = boto3.client('rds')
s3_client = boto3.client('s3')
cloudwatch_client = boto3.client('cloudwatch')

# cf curl "/v3/service_instances/92703ccc-4141-4a9c-9924-0a50ec65c29b?fields[service_plan.service_offering.service_broker]=name,guid&fields[service_plan.service_offering]=name&fields[service_plan]=name"
# cf curl "/v3/service_instances/92703ccc-4141-4a9c-9924-0a50ec65c29b?fields[service_plan]=name"

class AWSResource:
    def __init__(self, arn, tags):
        self.arn = arn
        self.tags = tags
        if ':' in arn: 
            self.instance_id = arn.split(':')[-1] 
        else:
            self.instance_id = "Unknown"

class AWSNotS3(AWSResource):
    def __init__(self, arn, tags):
        super().__init__(arn, tags) 
        self.instance_guid     = [ tag['Value'] for tag in tags if tag['Key'] == "Instance GUID"][0]
        self.space_guid         = [ tag['Value'] for tag in tags if tag['Key'] == "Space GUID"][0]
        try:
            self.space_name         = [ tag['Value'] for tag in tags if tag['Key'] == "Space name"][0]
        except: 
            self.space_name = self.get_cf_entity_name("spaces", self.space_guid)

        # FIXME: Maybe we shouldn't trust the plan name in the tag, but it's faster
        try:
            self.service_plan_name  = [ tag['Value'] for tag in tags if tag['Key'] == "Service plan name"][0]
        except: 
            try:
                self.service_plan_name = self.get_instance_plan_name(self.instance_guid)
            except: self.service_plan_name = "Not FOUND"

        # 'instance_name' could change with `cf rename-service`
        try:
            self.instance_name      = [ tag['Value'] for tag in tags if tag['Key'] == "Instance name"][0]
        except: self.instance_name = "In Name tbd"

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
            "cf curl /v3/service_instances/" + instance_guid + "/?fields[service_plan]=name",
            universal_newlines=True,
            shell=True,
        )
        cf_data = json.loads(cf_json)
        # FIX: This will fail if the 'included' field is missing
        return cf_data.get("included", "N/A")['service_plans'][0]['name']


class Rds(AWSNotS3):
    def __init__(self, arn, tags):
        super().__init__(arn, tags) 

    def get_db_instance(self, client):
        response = client.describe_db_instances(
            DBInstanceIdentifier = self.arn
        )
        instance_info = response['DBInstances'][0]
        self.allocated_storage = instance_info['AllocatedStorage']

class Redis(AWSNotS3):
    def __init__(self, arn, tags):
        super().__init__(arn, tags) 

class Es(AWSNotS3):
    def __init__(self, arn, tags):
        super().__init__(arn, tags) 

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
                {
                    "Name":"BucketName",
                    "Value":self.bucket_name
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
        self.s3_usage = 0
        datapoints = response['Datapoints']
        if len(datapoints) > 0 :
            self.s3_usage = datapoints[0]['Average']

class Organization:
    def __init__(self, name):
        self.name = name
        self.data = self.get_data()
        self.guid = self.data['guid']
        self.quota_guid = self.data['relationships']['quota']['data']['guid']
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
        return json.loads(cf_json)['resources'][0]
    
    def get_quota_memory(self):
        cf_json = subprocess.check_output(
            "cf curl /v3/organization_quotas/" + self.quota_guid,
            universal_newlines=True,
            shell=True,
        )
        return json.loads(cf_json)['apps']['total_memory_in_mb']

    def get_memory_usage(self):
        cf_json = subprocess.check_output(
            "cf curl /v3/organizations/" + self.guid + "/usage_summary",
            universal_newlines=True,
            shell=True,
        )
        return json.loads(cf_json)['usage_summary']['memory_in_mb']
    
    def get_rds_instances(self, client):
        tag_key = "Organization GUID"
        tag_value = self.guid
        response = client.get_resources(
            TagFilters = [
                {
                    'Key': tag_key,
                    'Values': [tag_value]
        
                }
            ],
            ResourceTypeFilters = ['rds:db']
        )
        for resource in response['ResourceTagMappingList']:
            rds = Rds(resource['ResourceARN'], resource['Tags'])
            self.rds_instances.append(rds)
    
    def get_redis_instances(self, client):
        tag_key = "Organization GUID"
        tag_value = self.guid
        response = client.get_resources(
            TagFilters = [
                {
                    'Key': tag_key,
                    'Values': [tag_value]
        
                }
            ],
            ResourceTypeFilters = ['elasticache:replicationgroup']
        )
        for resource in response['ResourceTagMappingList']:
            redis = Redis(resource['ResourceARN'], resource['Tags'])
            self.redis_instances.append(redis)

    def get_es_instances(self, client):
        tag_key = "Organization GUID"
        tag_value = self.guid
        response = client.get_resources(
            TagFilters = [
                {
                    'Key': tag_key,
                    'Values': [tag_value]
        
                }
            ],
            ResourceTypeFilters = ['es:domain']
        )
        for resource in response['ResourceTagMappingList']:
            es = Es(resource['ResourceARN'], resource['Tags'])
            self.es_instances.append(es)

    def get_s3_buckets(self, client):
        tag_value = self.guid
        for key_value in ["Organization GUID", "Organization ID", "organizationGuid"]:
            response = client.get_resources(
                TagFilters = [
                    {
                        'Key': key_value,
                        'Values': [tag_value]
                    }
                ],
                ResourceTypeFilters = ['s3:bucket']
            )
            for resource in response['ResourceTagMappingList']:
                s3 = S3(resource['ResourceARN'], resource['Tags'])
                self.s3_buckets.append(s3)

def test_authenticated():
    '''
    Try CF and AWS commands to ensure we're logged in to everything
    '''
    for cmd in ['cf oauth-token', 'aws sts get-caller-identity']:
        try:
            result = subprocess.run(
                cmd.split(' '), 
                check=True, 
                stderr = subprocess.DEVNULL,
                stdout = subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            print(f"Error: Command \"{cmd}\" failed, are you sure you're authenticated?", file=sys.stderr)
            sys.exit(1)  # Exit with non-zero status cod

def main():
    print("Skip auth test")
#    test_authenticated()
    # org = Organization(name="sandbox-gsa")
    # org = Organization(name="epa-avert")
    # org = Organization(name="cloud-gov-operators")
    # FAS Fedsim has all the types
    org = Organization(name="gsa-fas-fedsim")
    org.get_rds_instances(tags_client)
    for rds in org.rds_instances:
        rds.get_db_instance(rds_client)
    org.get_s3_buckets(tags_client)
    for s3 in org.s3_buckets:
        s3.get_s3_usage(cloudwatch_client)
    org.get_redis_instances(tags_client)
    org.get_es_instances(tags_client)

    print(f"Organization name: {org.name}")
    print(f"Organization GUID: {org.guid}")
    print(f"Organization memory quota: {org.get_quota_memory()}")
    print(f"Organization memory usage: {org.get_memory_usage()}")

    print("RDS:")
    rds_instance_plans = Counter()
    rds_allocation = 0
    for rds in org.rds_instances:
        rds_instance_plans[rds.service_plan_name] += 1
        rds_allocation += rds.allocated_storage
    for key, value in rds_instance_plans.items():
        print(f" {key}: {value}")
    print(f" RDS allocation (GB): {rds_allocation}")

    redis_instance_plans = Counter()
    print("Redis:")
    for redis in org.redis_instances:
        redis_instance_plans[redis.service_plan_name] += 1
    for key, value in redis_instance_plans.items():
        print(f" {key}: {value}")


    es_instance_plans = Counter()
    print("ES")
    for es in org.es_instances:
        es_instance_plans[es.service_plan_name] += 1
    for key, value in es_instance_plans.items():
        print(f" {key}: {value}")

    s3_total_storage = 0
    print("S3")
    for s in org.s3_buckets:
        s3_total_storage += s.s3_usage
    print(f" S3 Total Usage (GB): {s3_total_storage/(1024*1024):.2f}")

if __name__ == "__main__":
    main()
