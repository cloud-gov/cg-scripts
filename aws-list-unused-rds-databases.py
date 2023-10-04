# Purpose: Scrape the AWS RDS endpoints for the list of of databases and retrieve the connection history
# Usage: python3 aws-list-unused-rds-databases.py 
# Environment variables:
#  - NUM_DAYS: The number of days of no db connections to be included on the list, default is 30
#  - CSV_FILE_NAME: The results are written to a csv file, the default is "idle_db.csv"
#  - SHOW_ALL: Emit results for ALL databases, not just those with no db connections, default is false

import boto3
import csv, sys, os 
from datetime import datetime, timedelta, timezone


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
    header_row = ("DBInstanceIdentifier","DBInstanceClass","DBName","AllocatedStorage","Engine","EngineVersion","DB Connections","Created At","Age in Days","Org ID", "Space ID","Stop Command","TagList")
    obj.writerow(header_row)

    for page in paginator:
        for dbinstance in page['DBInstances']:
            db_instance_name = dbinstance['DBInstanceIdentifier']
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
            org_id = ""
            space_id = ""
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
                Period=3600 * 24 * int(num_days_history),
                Statistics=[
                    'Sum',
                ],
                Unit='Count'
            )

            # Try loop is here because if the rds is brand new, it will error out trying to pull cloudwatch stats
            try:
                connection_count = rds_conn_metric['Datapoints'][0]['Sum']
                print(f'Collecting information for: {db_instance_name}')

            except:
                print(f'Probably a new born db, could not pull cloudwatch metrics, setting value to -1: {db_instance_name}')
                connection_count = -1

            if (connection_count == 0.0 and db_age.days >= num_days_history) or show_all:
                output = (db_instance_name,db_type,db_name,db_storage,db_engine,db_engine_version, connection_count, db_instance_created_at, db_age.days, org_id, space_id, stop_command, db_tag_list)
                obj.writerow(output)


                #sys.exit(0)
def main():
  export_idle_dbs()

if __name__ == "__main__":
  main()

