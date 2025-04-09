#!/usr/bin/env python3

import subprocess
import sys
import json

# Option 1: Using a class
class Organization:
    def __init__(self, name):
        self.name = name
        self.guid = self.fetch_guid()

    def fetch_guid(self):
        cf_json = subprocess.check_output(
            "cf curl /v3/organizations/?names=" + self.name,
            universal_newlines=True,
            shell=True,
        )
        cf_data = json.loads(cf_json)
        return cf_data['resources'][0]['guid']
    
# Get the guid for the organization
#guid=$(echo $org | jq -j '.resources[] | .guid')
    



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
    org = Organization(name="sandbox-gsa")
    print(f"Organization name: {org.name}")
    print(f"Organization GUID: {org.guid}")


if __name__ == "__main__":
    main()
