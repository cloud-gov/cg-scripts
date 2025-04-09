#!/usr/bin/env python3

import subprocess
import sys
import json
import boto3
import datetime

tags_client = boto3.client('resourcegroupstaggingapi')
rds_client = boto3.client('rds')
s3_client = boto3.client('s3')
cloudwatch_client = boto3.client('cloudwatch')

class AWSResource:
    def __init__(self, arn, tags):
        self.arn = arn
        self.tags = tags
        if ':' in arn: 
            self.instance_id = arn.split(':')[-1] 
        else:
            self.instance_id = "Unknown"

class Rds(AWSResource):
    def __init__(self, arn, tags):
        super().__init__(arn, tags) 
        self.space_name         = [ tag['Value'] for tag in tags if tag['Key'] == "Space name"][0]
        self.space_guid         = [ tag['Value'] for tag in tags if tag['Key'] == "Space GUID"][0]
        self.service_plan_name  = [ tag['Value'] for tag in tags if tag['Key'] == "Service plan name"][0] # This could change with `cf rename-service`
        self.instance_name      = [ tag['Value'] for tag in tags if tag['Key'] == "Instance name"][0]

    def get_db_instance(self, client):
        response = client.describe_db_instances(
            DBInstanceIdentifier = self.arn
        )
        instance_info = response['DBInstances'][0]
        self.allocated_storage = instance_info['AllocatedStorage']

class S3(AWSResource):
    def __init__(self, arn, tags):
        super().__init__(arn, tags) 

    def get_s3_usage(self, client):
        now = datetime.datetime.now()
        self.s3_usage = client.get_metric_statistics(
            Namespace="AWS/S3",
            MetricName="BucketSizeBytes",
            Dimensions=[
                {
                    "Name":"BucketName",
                    "Value":self.arn
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

class Organization:
    def __init__(self, name):
        self.name = name
        self.data = self.get_data()
        self.guid = self.data['guid']
        self.quota_guid = self.data['relationships']['quota']['data']['guid']
        self.rds_instances = []
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
            # r = resource['ResourceARN']
            rds = Rds(resource['ResourceARN'], resource['Tags'])
            self.rds_instances.append(rds)

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
    test_authenticated()
    #org = Organization(name="sandbox-gsa")
    org = Organization(name="cloud-gov-operators")
    org.get_rds_instances(tags_client)
    for rds in org.rds_instances:
        rds.get_db_instance(rds_client)
    org.get_s3_buckets(tags_client)
    for s3 in org.s3_buckets:
        s3.get_s3_usage(cloudwatch_client)

    print(f"Organization name: {org.name}")
    print(f"Organization GUID: {org.guid}")
    print(f"Organization memory quota: {org.get_quota_memory()}")
    print(f"Organization memory usage: {org.get_memory_usage()}")
    for r in org.rds_instances:
        print(f" RDS allocation (GB): {r.allocated_storage}")
        print(f" RDS service plan name: {r.service_plan_name}")
    for s in org.s3_buckets:
        print(f" S3 ARN: {s.arn}")
        print(f" S3 Usage (GB) {s.s3_usage}")

if __name__ == "__main__":
    main()
