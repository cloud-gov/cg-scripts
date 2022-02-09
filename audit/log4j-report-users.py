#!/usr/bin/env python3

import json
import os
import subprocess
import sys
import re

from cloudfoundry_client.client import CloudFoundryClient
config_file = os.path.join(os.path.expanduser("~"), ".cf_client_python.json")

# If this fail, run `cf login --sso`, then `cloudfoundry-client import_from_cf_cli`

with open(config_file, "r") as f:
    configuration = json.load(f)
    client = CloudFoundryClient(configuration["target_endpoint"], verify=configuration["verify"])
    client.init_with_token(configuration["refresh_token"])

import csv
csvwriter = csv.writer(sys.stdout,quoting=csv.QUOTE_ALL)
csvwriter.writerow([ "App Name", "Space Name", "Org Name", "Org Managers", "Space Devs" ])

app_guid_file = open("app_guids", "r")
app_guid = app_guid_file.readline().strip()
while app_guid:
    if re.match(r'docker', app_guid ):
        csvwriter.writerow(
            [ "null",
              "null",
              "null",
              "null",
              "null"
            ])
    else:
        app = client.v3.apps.get(app_guid)
        space = app.space()
        org = space.organization()

        sp_cf = f"cf space-users {org['name']} {space['name']}"
        sp_perl = ' | perl -ne \'if (/SPACE DEVELOPER/ .. /^$/) { next unless /@/; m/([a-z\.\]+@[a-z\.]+)/ and print "$1,"}\''
        sp_cmd = sp_cf + sp_perl
        sp_out = subprocess.check_output(sp_cmd, shell=True, text=True)

        org_cf = f"cf org-users {org['name']}"
        org_perl = ' | perl -ne \'if (/ORG MANAGER/ .. /^$/) { next unless /@/; m/([a-z\.\]+@[a-z\.]+)/ and print "$1,"}\''
        org_cmd = org_cf + org_perl
        org_out = subprocess.check_output(org_cmd, shell=True, text=True)

        csvwriter.writerow(
            [ app['name'],
            space['name'],
            org['name'],
            org_out,
            sp_out
            ])
        
    app_guid = app_guid_file.readline().strip()

app_guid_file.close()   