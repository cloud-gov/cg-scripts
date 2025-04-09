#!/usr/bin/env python3

import subprocess
import sys
import json
import boto3

tags_client = boto3.client('resourcegroupstaggingapi')

class Rds:
    def __init__(self, arn, tags):
        self.arn = arn
        self.tags = tags
        if ':' in arn: 
            self.instance_id = arn.split(':')[-1] 
        else:
            self.instance_id = "Unknown"
        self.space_name         = [ tag['Value'] for tag in tags if tag['Key'] == "Space name"]
        self.space_guid         = [ tag['Value'] for tag in tags if tag['Key'] == "Space guid"]
        self.service_plan_name  = [ tag['Value'] for tag in tags if tag['Key'] == "Service plan name"]
        self.instance_name      = [ tag['Value'] for tag in tags if tag['Key'] == "Instance name"][0]

class Organization:
    def __init__(self, name):
        self.name = name
        self.data = self.get_data()
        self.guid = self.data['guid']
        self.quota_guid = self.data['relationships']['quota']['data']['guid']
        self.rds_instances = []

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
    # test_authenticated()
    org = Organization(name="cloud-gov-operators")
    org.get_rds_instances(tags_client)

    print(f"Organization name: {org.name}")
    print(f"Organization GUID: {org.guid}")
    print(f"Organization memory quota: {org.get_quota_memory()}")
    print(f"Organization memory usage: {org.get_memory_usage()}")
    for r in org.rds_instances:
        print(f" RDS ARN: {r.arn}")
        print(f" RDS instance: {r.instance_name}")

if __name__ == "__main__":
    main()
