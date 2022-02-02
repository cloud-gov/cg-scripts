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


for organization in client.v2.organizations:
    print(organization['metadata']['guid'])
