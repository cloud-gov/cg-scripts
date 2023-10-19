# Purpose: Scrape the AWS ElasticSearch endpoints for the list of of domains and retrieve the number of searchable documents,
#          Primarily used to find unused Elasticsearch/OpenSearch domains.
# Prerequisites:
#  - Use aws-vault if running locally
#  - `cf login` into production CF
#  - The 12 digit AWS account number
# Usage: AWS_ACCOUNT=123456789012 python3 aws-list-unused-es-domains.py 
# Environment variables:
#  - AWS_ACCOUNT: The 12 digit AWS account number, probably want gov prod plat admin
#  - SHOW_ALL: Emit results for ALL databases, not just those with no db connections, default is false
#  - SYSTEM_DOMAIN: CF system domain, default is pointed to production with the value "fr.cloud.gov"


import boto3
import sys, os 
import requests, warnings
import subprocess
from requests.structures import CaseInsensitiveDict
from datetime import datetime, timedelta


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






def export_domains():

    # Set defaults 
    show_all = os.getenv('SHOW_ALL', False )
    aws_account = os.getenv('AWS_ACCOUNT','NOTFOUND')
    comma = ","


    # Check that AWS Account number has been provided
    if aws_account == "NOTFOUND" or len(aws_account) != 12:
        print("Please set the 12 digit AWS_ACCOUNT variable and try again.")
        sys.exit(1)

    # Set history
    num_days_history = 1
    start_time = datetime.now() - timedelta(days=int(num_days_history))
    end_time = datetime.now()
    
    cloudwatch_client = boto3.client('cloudwatch', region_name='us-gov-west-1')
    es_client = boto3.client('opensearch')

    domains = es_client.list_domain_names()

    # Print header
    print("domain_name, org_id, space_id, instance_guid, max_searchable_documents, org_name, space_name, instance_name")

    for esinstance in domains['DomainNames']:
        domain_name = esinstance['DomainName']

        domain = es_client.describe_domain(DomainName=domain_name)
        arn = domain['DomainStatus']['ARN']
        tags = es_client.list_tags(ARN=arn)

        for tag in tags['TagList']:
            if tag['Key'] == "Organization GUID":
                org_id = tag['Value']
            if tag['Key'] == "Space GUID":
                space_id = tag['Value']
            if tag['Key'] == "Instance GUID":
                instance_guid = tag['Value']


        es_metrics = cloudwatch_client.get_metric_statistics(
            Namespace='AWS/ES',
            MetricName='SearchableDocuments',
            Dimensions=[
                {
                    'Name': 'DomainName',
                    'Value': domain_name
                },
                {
                    "Name": "ClientId",
                    "Value": aws_account
                }
            ],
            StartTime= start_time,
            EndTime= end_time,
            Period= 14400,  
            Statistics=[
                'Maximum',
            ]
        )

        max_searchable_documents = 0
        for es_metric in es_metrics['Datapoints']:
            searchable_documents = es_metric['Maximum']
            if searchable_documents > max_searchable_documents:
                max_searchable_documents = searchable_documents

        if max_searchable_documents == 0.0  or show_all:
            org_name = space_name = instance_name = ""
            if space_id != "":
                org_name, space_name, instance_name = get_org_space_service_instance(space_id, instance_guid)  #Only lookup org/space name if needed because of performance hit
            print(domain_name,comma, org_id,comma, space_id,comma, instance_guid,comma, max_searchable_documents,comma, org_name,comma, space_name,comma, instance_name)


def main():
  export_domains()

if __name__ == "__main__":
  main()

