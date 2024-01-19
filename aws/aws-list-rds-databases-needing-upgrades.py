# Purpose: Scrape the AWS RDS endpoints for the list of of databases and retrieve the list of RDS instances
#          needing upgrades to the instance family or db engine
# Prerequisites:
#  - Use aws-vault if running locally
#  - `cf login` into production CF
# Usage: python3 aws-list-rds-databases-needing-upgrades.py 
# Environment variables:
#  - CSV_FILE_NAME: The results are written to a csv file, the default is "idle_db.csv"
#  - SYSTEM_DOMAIN: CF system domain, default is pointed to production with the value "fr.cloud.gov"

import boto3
import csv, sys, os 
import requests, warnings
import subprocess
from requests.structures import CaseInsensitiveDict
from datetime import datetime, timezone


# Function to retrieve org and space name for an app
def get_org_space_service_instance(space_id, instance_id):

    if not sys.warnoptions:
        warnings.simplefilter("ignore")

    # Login
    system_domain = os.getenv('SYSTEM_DOMAIN', "fr.cloud.gov" )

    # This is done each time because the overall script takes longer to run than the token is good for
    result = subprocess.run(['cf', 'oauth-token'], stdout=subprocess.PIPE)
    token = result.stdout
    token = token[:-1] # Need to trim the newline character at the end 
   

    headers = CaseInsensitiveDict()
    headers["Accept"] = "application/json"
    headers["Authorization"] = token

    space_url = "https://api." + system_domain + "/v3/spaces/" + space_id

    # Try/except because the org id might not exist for the CF environment targeted (typically dev/staging).  
    try:
        space_vars = requests.get(space_url, headers=headers, verify=False).json()
        space_name = space_vars["name"]
        org_url = space_vars["links"]["organization"]["href"]
        org_vars = requests.get(org_url, headers=headers, verify=False).json()
        org_name = org_vars["name"]
    except:
        org_name="NOTFOUND"
        space_name="NOTFOUND"

    try:
        service_instance_url = "https://api." + system_domain + "/v3/service_instances/" + instance_id
        service_instance_vars = requests.get(service_instance_url, headers=headers, verify=False).json()
        instance_name = service_instance_vars["name"]
    except:
        instance_name="NOTFOUND"


    return org_name, space_name, instance_name

# Business logic on what to do with the instance
def determine_action(db_engine_version, family_name, db_instance_name):

    action = ""
    family_ok = True
    engine_ok = True

    if family_name == "db.t2" or family_name == "db.m4":
        family_ok = False

    if db_engine_version == "11.19" or db_engine_version == "5.7.42":
        engine_ok = False

    if family_ok==False and engine_ok==False:
        # Needs instance and engine upgrade
        if db_instance_name.startswith("cg-aws-broker-dev"):
            action = "Give to platform, needs both engine upgrade and instance upgrade, is AWS broker dev broker"
        elif db_instance_name.startswith("cg-aws-broker-stage"):
            action = "Give to platform, needs both engine upgrade and instance upgrade, is AWS broker staging broker"
        elif db_instance_name.startswith("development-"):
            action = "Give to platform, needs both engine upgrade and instance upgrade, likely terraform created in cg-provision main stack for development"
        elif db_instance_name.startswith("staging-"):
            action = "Give to platform, needs both engine upgrade and instance upgrade, likely terraform created in cg-provision main stack for staging"
        elif db_instance_name.startswith("production-"):
            action = "Give to platform, needs both engine upgrade and instance upgrade, likely terraform created in cg-provision main stack for production"
        elif db_instance_name.startswith("tooling-"):
            action = "Give to platform, needs both engine upgrade and instance upgrade, likely terraform created in cg-provision main stack for tooling"
        elif db_instance_name.startswith("terraform-"):
            action = "Give to platform, needs both engine upgrade and instance upgrade, likely terraform but need to track down"
        elif db_instance_name.startswith("bosh-"):
            action = "Give to platform, needs both engine upgrade and instance upgrade, likely terraform but need to track down"
        else:
            action = "Customer database which needs both engine upgrade and instance upgrade"

    elif family_ok==False and engine_ok:
        # Needs just instance upgraded
        if db_instance_name.startswith("cg-aws-broker-dev"):
            action = "Give to platform, needs instance upgrade, is AWS broker dev broker"
        elif db_instance_name.startswith("cg-aws-broker-stage"):
            action = "Give to platform, needs intance upgrade, is AWS broker staging broker"
        elif db_instance_name.startswith("development-"):
            action = "Give to platform, needs instance upgrade, likely terraform created in cg-provision main stack for development"
        elif db_instance_name.startswith("staging-"):
            action = "Give to platform, needs instance upgrade, likely terraform created in cg-provision main stack for staging"
        elif db_instance_name.startswith("production-"):
            action = "Give to platform, needs instance upgrade, likely terraform created in cg-provision main stack for production"
        elif db_instance_name.startswith("tooling-"):
            action = "Give to platform, needs instance upgrade, likely terraform created in cg-provision main stack for tooling"
        elif db_instance_name.startswith("terraform-"):
            action = "Give to platform, needs instance upgrade, likely terraform but need to track down"
        elif db_instance_name.startswith("bosh-"):
            action = "Give to platform, needs instance upgrade, likely terraform but need to track down"
        else:
            action = "Customer database which needs instance upgrade"

    elif family_ok and engine_ok==False:
        # Needs engine upgraded
        if db_instance_name.startswith("cg-aws-broker-dev"):
            action = "Give to platform, needs engine upgrade, is AWS broker dev broker"
        elif db_instance_name.startswith("cg-aws-broker-stage"):
            action = "Give to platform, needs engine upgrade, is AWS broker staging broker"
        elif db_instance_name.startswith("development-"):
            action = "Give to platform, needs engine upgrade, likely terraform created in cg-provision main stack for development"
        elif db_instance_name.startswith("staging-"):
            action = "Give to platform, needs engine upgrade, likely terraform created in cg-provision main stack for staging"
        elif db_instance_name.startswith("production-"):
            action = "Give to platform, needs engine upgrade, likely terraform created in cg-provision main stack for production"
        elif db_instance_name.startswith("tooling-"):
            action = "Give to platform, needs engine upgrade, likely terraform created in cg-provision main stack for tooling"
        elif db_instance_name.startswith("terraform-"):
            action = "Give to platform, needs engine upgrade, likely terraform but need to track down"
        elif db_instance_name.startswith("bosh-"):
            action = "Give to platform, needs engine upgrade, likely terraform but need to track down"
        else:
            action = "Customer database which needs engine upgrade"

    else:
        action = "ok"

    return action



def export_dbs():

    # Set defaults 
    csv_file_name = os.getenv('CSV_FILE_NAME', "rds_db.csv" )

    # Set history
    end_time = datetime.now(tz=timezone.utc)


    csv_file = open(csv_file_name, 'w')
    obj = csv.writer(csv_file, delimiter=',')

    rds = boto3.client('rds')
    paginator = rds.get_paginator('describe_db_instances').paginate()

    # Create and write out header row for csv file
    header_row = ("DBInstanceIdentifier","DBInstanceClass","DBName","AllocatedStorage","Engine","EngineVersion","PreferredMaintenanceWindow","Action", "Created At","Age in Days","Org ID", "Org Name", "Space ID", "Space Name", "Instance ID", "Instance Name", "TagList")
    obj.writerow(header_row)

    for page in paginator:
        for dbinstance in page['DBInstances']:
            db_instance_name = dbinstance['DBInstanceIdentifier']
            print(f'Collecting information for: {db_instance_name}')
            
            db_type = dbinstance['DBInstanceClass']
            db_name = dbinstance['DBName']
            db_storage = dbinstance['AllocatedStorage']
            db_engine = dbinstance['Engine']
            db_engine_version = dbinstance['EngineVersion']
            db_instance_created_at = dbinstance['InstanceCreateTime']
            db_age = end_time - db_instance_created_at
            db_tag_list = dbinstance['TagList']
            db_preferred_maintenance_windows = dbinstance['PreferredMaintenanceWindow']

            family_name = "db." + db_type.split('.')[1]

            # Pull the org and space id's from the tags
            org_id = space_id = instance_guid = ""

            for tagArray in db_tag_list:
                if tagArray['Key'] == "Organization GUID":
                    org_id = tagArray['Value']
                if tagArray['Key'] == "Space GUID":
                    space_id = tagArray['Value']
                if tagArray['Key'] == "Instance GUID":
                    instance_guid = tagArray['Value']

            action = determine_action(db_engine_version, family_name, db_instance_name )

            if action != "ok":
                org_name = space_name = instance_name = ""
                if space_id != "":
                    org_name, space_name, instance_name = get_org_space_service_instance(space_id, instance_guid)  #Only lookup org/space name if needed because of performance hit

                output = (db_instance_name,db_type, db_name,db_storage,db_engine,db_engine_version, db_preferred_maintenance_windows,action, db_instance_created_at, db_age.days, org_id, org_name, space_id, space_name, instance_guid, instance_name, db_tag_list)
                obj.writerow(output)


def main():
  export_dbs()

if __name__ == "__main__":
  main()

