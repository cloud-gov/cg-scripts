# Purpose: Scrape the AWS Elasticache endpoints for the list of Redis clusters and retrieve the Current Items history
# Prerequisites:
#  - Use aws-vault if running locally
#  - `cf login` into production CF
# Usage: python3 aws-list-unused-redis-clusters.py 
# Environment variables:
#  - NUM_DAYS: The number of days of no db connections to be included on the list, default is 30
#  - SHOW_ALL: Emit results for ALL databases, not just those with no db connections, default is false
#  - SYSTEM_DOMAIN: CF system domain, default is pointed to production with the value "fr.cloud.gov"



import boto3, sys, os
import requests, warnings
import subprocess
from requests.structures import CaseInsensitiveDict
from datetime import datetime, timedelta

# Function to retrieve org and space name for an app
def get_org_space_service_instance(instance_id):

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

    service_instance_url = "https://api." + system_domain + "/v3/service_instances/" + instance_id
    service_instance_vars = requests.get(service_instance_url, headers=headers, verify=False).json()
    
    # Try/except because the org id might not exist for the CF environment targeted (typically dev/staging).  
    try:
        instance_name = service_instance_vars["name"]

        space_url = service_instance_vars["links"]["space"]["href"]
        space_vars = requests.get(space_url, headers=headers, verify=False).json()
        space_name = space_vars["name"]

        org_url = space_vars["links"]["organization"]["href"]
        org_vars = requests.get(org_url, headers=headers, verify=False).json()
        org_name = org_vars["name"]

    except:
        org_name="NOTFOUND"
        space_name="NOTFOUND"
        instance_name="NOTFOUND"
    return org_name, space_name, instance_name

def export_idle_redis():

    # Set defaults 
    num_days_history = os.getenv('NUM_DAYS', 30)
    show_all = os.getenv('SHOW_ALL', False )
    comma = ","

    # Set history
    start_time = datetime.now() - timedelta(days=int(num_days_history))
    end_time = datetime.now()
    cluster_max_curr_items = 0

    cloudwatch_client = boto3.client('cloudwatch', region_name='us-gov-west-1')
    ec_client = boto3.client('elasticache')

    # Print header
    print( "cluster_id, node_type, engine, engine_version, status, instance_guid, cluster_max_curr_items, org_name, space_name, instance_name")


    # Note this loops through each Redis node, not the cluster.  For cluster only, switch to `describe_replication_groups`
    paginator = ec_client.get_paginator('describe_cache_clusters').paginate()
    last_cluster_id = ""

    for page in paginator:
        for cluster_node in page['CacheClusters']:
            cluster_node_id = cluster_node['CacheClusterId']
            cluster_id = cluster_node_id[:-4]
            node_type = cluster_node['CacheNodeType']
            engine = cluster_node['Engine']
            engine_version = cluster_node['EngineVersion']
            status = cluster_node['CacheClusterStatus']
            instance_guid = cluster_node_id[4:-4]

            ec_metrics = cloudwatch_client.get_metric_statistics(
                Namespace='AWS/ElastiCache',
                MetricName='CurrItems',
                Dimensions=[
                    {
                        'Name': 'CacheClusterId',
                        'Value': cluster_node_id
                    }
                ],
                StartTime= start_time,
                EndTime= end_time,
                Period= 86400,  
                Statistics=[
                    'Maximum',
                ]
            )

            # Find the highwater mark of "Current Items", per day, for each cluster node and aggregate for the whole cluster
            node_max_curr_items = 0
            for es_metric in ec_metrics['Datapoints']:
                curr_items = es_metric['Maximum']
                if curr_items > node_max_curr_items:
                    node_max_curr_items = curr_items
            cluster_max_curr_items = cluster_max_curr_items + node_max_curr_items


            if last_cluster_id != cluster_id:

                # Got to the last node in the cluster
                org_name = space_name = instance_name = ""
                org_name, space_name, instance_name = get_org_space_service_instance(instance_guid)  #Only lookup org/space name if needed because of performance hit

                if show_all or cluster_max_curr_items == 0.0:
                    print(cluster_id, comma, node_type, comma, engine, comma, engine_version, comma, status, comma, instance_guid, comma, cluster_max_curr_items, comma, org_name, comma, space_name, comma, instance_name)
                cluster_max_curr_items = 0
                last_cluster_id = cluster_id


def main():
  export_idle_redis()

if __name__ == "__main__":
  main()


