#!/usr/bin/env python3

import json
import os
import subprocess

from cloudfoundry_client.client import CloudFoundryClient
config_file = os.path.join(os.path.expanduser("~"), ".cf_client_python.json")

# If this fail, run `cf login --sso`, then `cloudfoundry-client import_from_cf_cli`

with open(config_file, "r") as f:
    configuration = json.load(f)
    client = CloudFoundryClient(configuration["target_endpoint"], verify=configuration["verify"])
    client.init_with_token(configuration["refresh_token"])

app_guid = "a4dafcbf-16a4-4ee4-a1a3-1fed3fb2402d"
app = client.v3.apps.get(app_guid)
space = app.space()
org = space.organization()
m= (f"\"{app['name']}\", \"{space['name']}\", \"{org['name']}\"")

s = f"cf space-users {org['name']} {space['name']}"
s = f"cf space-users gsa-forms-prototyping MiA" 
p = ' | perl -ne \'if (/SPACE DEVELOPER/ .. /^$/) { next unless /@/; m/([a-z\.\]+@[a-z\.]+)/ and print "$1,"}\''
full_cmd = s + p

out = subprocess.check_output(full_cmd, shell=True, text=True)

print(m, ", \"", out, "\"" )