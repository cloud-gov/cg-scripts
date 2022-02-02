#!/usr/bin/env python3

import json
import os

from cloudfoundry_client.client import CloudFoundryClient
config_file = os.path.join(os.path.expanduser("~"), ".cf_client_python.json")

# If this fail, run `cf login --sso`, then `cloudfoundry-client import_from_cf_cli`

with open(config_file, "r") as f:
    configuration = json.load(f)
    client = CloudFoundryClient(configuration["target_endpoint"], verify=configuration["verify"])
    client.init_with_token(configuration["refresh_token"])

#app_guids = 
#with open(app_guids, "r") as r:
#    for guid in r.readlines():
#        print(guid)
app_guid = "a4dafcbf-16a4-4ee4-a1a3-1fed3fb2402d"
app = client.v3.apps.get(app_guid)
print("App name: %s" % app["name"])
space = app.space()
print("Space name: %s" % space["name"])
org = space.organization()
print("Org name: %s" % org["name"])

