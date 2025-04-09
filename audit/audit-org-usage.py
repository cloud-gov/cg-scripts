#!/usr/bin/env python3

import subprocess
import sys
import json

# Option 1: Using a class
class Organization:
    def __init__(self, name):
        self.name = name
        self.data = self.get_data()
        self.guid = self.data['guid']
        self.quota_guid = self.data['relationships']['quota']['data']['guid']

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
    print(f"Organization name: {org.name}")
    print(f"Organization GUID: {org.guid}")
    print(f"Organization memory quota: {org.get_quota_memory()}")
    print(f"Organization memory usage: {org.get_memory_usage()}")


if __name__ == "__main__":
    main()
