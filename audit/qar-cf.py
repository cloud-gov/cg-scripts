#!/usr/bin/env python3

# To run this locally, `gem install cf-uaac`, then set PATH
# export PATH=$PATH:/usr/local/lib/ruby/gems/3.2.0/bin/
# And 
# `uaac token client get admin -s $SECRET`
# where SECRET is from jumpbox (replace 'cf-staging' with your target env)
# `secret=$(credhub get -n /bosh/cf-staging/uaa_admin_client_secret | grep value | sed -r 's/value: //g')`

import subprocess
import json

users = [ ]
van = {
    "groups": ["admin-ui", "uaa-admin"],
    "uuid":""
}
users.append(van)

# for each user, update the UUID with their correct value

# d53109eb-f669-4ba5-9378-dddd8157f03a

# the for g in group, 
#   for each user, OK if UUID is present
#      fail if not present
# uaac users -a id  "username eq 'vanhnguyen'"

command = "uaac curl '/Users?attributes=id&filter=username+eq+%27vanhnguyen%27'"

try: 
    command = "uaac --bodyonly curl /Users"
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    users = json.loads(result.stdout)
    print(users["totalResults"])



except subprocess.CalledProcessError as e:
    print(f"Error running command: {e}")
    