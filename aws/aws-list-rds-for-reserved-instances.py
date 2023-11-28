# Purpose: Scrape the AWS RDS to determine reserved instances to purchase
# Prerequisites:
#  - Use aws-vault if running locally
# Usage: python3 aws-list-rds-for-reserved-instances.py 


import boto3

def calc_normalized_units(instance_size, multi_az):
    units = -1000000000000000  #make it obvious instance size value didn't match
    if instance_size=="micro":
        units = 0.5
    elif instance_size == "small":
        units = 1
    elif instance_size == "medium":
        units = 2
    elif instance_size == "large":
        units = 4
    elif instance_size == "xlarge":
        units = 8
    elif instance_size == "2xlarge":
        units = 16
    elif instance_size == "4xlarge":
        units = 32
    elif instance_size == "6xlarge":
        units = 48
    elif instance_size == "8xlarge":
        units = 64
    elif instance_size == "10xlarge":
        units = 80
    elif instance_size == "12xlarge":
        units = 96
    elif instance_size == "16xlarge":
        units = 128
    elif instance_size == "24xlarge":
        units = 192
    elif instance_size == "32xlarge":
        units = 256

    if multi_az == True:
        units = units * 2

    return units


def export_ri_needed():

    rds = boto3.client('rds')
    paginator = rds.get_paginator('describe_db_instances').paginate()

    summary = []

    for page in paginator:
        for dbinstance in page['DBInstances']:

            #db_instance_name = dbinstance['DBInstanceIdentifier']
            db_type = dbinstance['DBInstanceClass']
            db_engine = dbinstance['Engine']
            multi_az = dbinstance['MultiAZ']
            family_name = "db." + db_type.split('.')[1]
            instance_size = db_type.split('.')[2]

            normalized_units = calc_normalized_units(instance_size, multi_az)

            if not any(d['family_name'] == family_name and d['db_engine'] == db_engine for d in summary):
                # Row doesn't exist, add it
                summary_dict = {
                    "family_name": family_name,
                    "db_engine": db_engine,
                    "normalized_units": normalized_units
                }
                summary.append(summary_dict)
            else:
                # Row exists, add normalized_units
                for summary_row in summary:
                    if summary_row['family_name'] == family_name and summary_row['db_engine'] == db_engine:
                        summary_row['normalized_units'] = summary_row['normalized_units'] + normalized_units

    for row in summary:
        print(row)


def main():
  export_ri_needed()

if __name__ == "__main__":
  main()
