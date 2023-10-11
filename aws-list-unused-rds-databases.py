# Purpose: Scrape the AWS RDS endpoints for the list of of databases and retrieve the connection history
# Prerequisites:
#  - Use aws-vault if running locally
#  - `cf login` into production CF
# Usage: python3 aws-list-unused-rds-databases.py 
# Environment variables:
#  - NUM_DAYS: The number of days of no db connections to be included on the list, default is 30
#  - CSV_FILE_NAME: The results are written to a csv file, the default is "idle_db.csv"
#  - SHOW_ALL: Emit results for ALL databases, not just those with no db connections, default is false
#  - SYSTEM_DOMAIN: CF system domain, default is pointed to production with the value "fr.cloud.gov"

import boto3
import csv, sys, os 
import requests, warnings
import subprocess
from requests.structures import CaseInsensitiveDict
from datetime import datetime, timedelta, timezone

# Function to retrieve org and space name for an app
def get_org_space(space_id):

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

    return org_name, space_name

# Business logic on what to do with the instance
def determine_action(connection_count, db_instance_name, space_name):

    action = ""
    if connection_count > 0.0:
        action = "Do nothing"
    elif db_instance_name.startswith("cg-aws-broker-prod") and space_name == "NOTFOUND":
        action = "Give to platform, is AWS broker prod but not valid space_id"
    elif db_instance_name.startswith("cg-aws-broker-prod") and space_name != "NOTFOUND" and space_name != "":
        action = "Lookup customer and contact to shutdown the instance"
    elif db_instance_name.startswith("cg-aws-broker-prod") and space_name == "":
        action = "Give to platform, is AWS broker prod but missing tags to associate to space_id"
    elif db_instance_name.startswith("cg-aws-broker-dev"):
        action = "Give to platform, is AWS broker dev broker"
    elif db_instance_name.startswith("cg-aws-broker-stage"):
        action = "Give to platform, is AWS broker staging broker"
    elif db_instance_name.startswith("development-"):
        action = "Give to platform, likely terraform created in cg-provision main stack for development"
    elif db_instance_name.startswith("staging-"):
        action = "Give to platform, likely terraform created in cg-provision main stack for staging"
    elif db_instance_name.startswith("production-"):
        action = "Give to platform, likely terraform created in cg-provision main stack for production"
    elif db_instance_name.startswith("tooling-"):
        action = "Give to platform, likely terraform created in cg-provision main stack for tooling"
    elif db_instance_name.startswith("terraform-"):
        action = "Give to platform, likely terraform but need to track down"
    else:
        action = "Give to platform, unclassified"
    return action

def export_idle_dbs():

    # Set defaults 
    num_days_history = os.getenv('NUM_DAYS', 30)
    csv_file_name = os.getenv('CSV_FILE_NAME', "idle_db.csv" )
    show_all = os.getenv('SHOW_ALL', False )

    # Set history
    start_time = datetime.now() - timedelta(days=int(num_days_history))
    end_time = datetime.now()
    end_time_utc = datetime.now(tz=timezone.utc)

    cloudwatch_client = boto3.client('cloudwatch', region_name='us-gov-west-1')

    csv_file = open(csv_file_name, 'w')
    obj = csv.writer(csv_file, delimiter=',')

    rds = boto3.client('rds')
    paginator = rds.get_paginator('describe_db_instances').paginate()

    # Create and write out header row for csv file
    header_row = ("DBInstanceIdentifier","DBInstanceClass","Action","DBName","AllocatedStorage","Engine","EngineVersion","DB Connections","Created At","Age in Days","Org ID", "Org Name", "Space ID", "Space Name", "Stop Command","TagList")
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
            db_age = end_time_utc - db_instance_created_at
            db_tag_list = dbinstance['TagList']
            stop_command = "aws rds stop-db-instance --db-instance-identifier mydbinstance " + db_instance_name + " ;"

            # Pull the org and space id's from the tags
            org_id = space_id = ""

            for tagArray in db_tag_list:
                if tagArray['Key'] == "Organization GUID":
                    org_id = tagArray['Value']
                if tagArray['Key'] == "Space GUID":
                    space_id = tagArray['Value']

            # Pull the cloudwatch db connections metrics for the db instance
            rds_conn_metric = cloudwatch_client.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName='DatabaseConnections',
                Dimensions=[
                    {
                        'Name': 'DBInstanceIdentifier',
                        'Value': db_instance_name
                    },
                ],
                StartTime= start_time,
                EndTime= end_time,
                Period= 86400,    # Pull 1 day's worth of stats
                Statistics=[
                    'Sum',
                ],
                Unit='Count'
            )

            # Try loop is here because if the rds is brand new, it will error out trying to pull cloudwatch stats
            try:
                connection_count = 0.0
                for datapoint in rds_conn_metric['Datapoints']:
                    connection_count = connection_count + datapoint['Sum']

            except:
                print(f'Probably a new born db, could not pull cloudwatch metrics, setting value to -1: {db_instance_name}')
                connection_count = -1

            if (connection_count == 0.0 and db_age.days >= num_days_history) or show_all:
                org_name = space_name = ""
                if space_id != "":
                    org_name, space_name = get_org_space(space_id)  #Only lookup org/space name if needed because of performance hit

                action = determine_action(connection_count, db_instance_name, space_name)
                output = (db_instance_name,db_type, action, db_name,db_storage,db_engine,db_engine_version, connection_count, db_instance_created_at, db_age.days, org_id, org_name, space_id, space_name, stop_command, db_tag_list)
                obj.writerow(output)



def main():
  export_idle_dbs()

if __name__ == "__main__":
  main()

