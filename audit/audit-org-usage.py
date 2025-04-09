#!/usr/bin/env python3

import subprocess
import sys
import json
import boto3

tags_client = boto3.client('resourcegroupstaggingapi')

class Rds:
    def __init__(self, arn):
        self.arn = arn

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
            ]
        )
        for resource in response['ResourceTagMappingList']:
            r = resource['ResourceARN']
            # rds = Rds(response['ResourceARN'])
            self.rds_instances.append(r)

#{ "ResourceTagMappingList": [ {
#            "ResourceARN": "arn:aws-us-gov:rds:us-gov-west-1:135676904304:db:cg-aws-broker-prodme3mx7or6nhflbj",
#            "Tags": [
#                {
#                    "Key": "Service offering name",
#                    "Value": "aws-rds"
#                },
#                {
#                    "Key": "Organization GUID",
#                    "Value": "77fa4cb4-963d-491d-ac73-23b6de945edd"
#                },


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
        print(f"RDS ARN: {r}")

if __name__ == "__main__":
    main()
