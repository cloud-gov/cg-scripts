#!/usr/bin/env python3

import subprocess
import json

try: 
    command = "uaac --bodyonly curl /Users"
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    users = json.loads(result.stdout)

except subprocess.CalledProcessError as e:
    print(f"Error running command: {e}")
    
print(users["totalResults"])