import argparse
import json
import datetime

import boto3

UPDATED_TAG = {"Key": "GeoRestriction", "Value": "Default"}

def main():
    args = get_args()
    client = boto3.client("cloudfront")
    distros = get_all_distros(client)
    if args.filters:
        distros = [distro for distro in distros if distro['id'] in args.filters]
    for distro in distros:
        distro['config']['Restrictions'] = RESTRICTIONS
        if args.update:
            client.update_distribution(DistributionConfig=distro['config'], Id=distro['id'], IfMatch=distro['etag'])
            client.tag_resource(Resource=distro['arn'], Tags=dict(Items=[UPDATED_TAG]))

    
def get_all_distros(client):
    distroresponse = client.list_distributions()
    distros = []
    for item in distroresponse['DistributionList']['Items']:
        cfg = client.get_distribution_config(Id=item['Id'])
        distros.append(dict(id=item['Id'], etag=cfg['ETag'], arn=item['ARN'], config=cfg['DistributionConfig']))
    while distroresponse['DistributionList'].get("NextMarker"):
        distroresponse = client.list_distributions(Marker=distroresponse['DistributionList']['NextMarker'])
        for item in distroresponse['DistributionList']['Items']:
            cfg = client.get_distribution_config(Id=item['Id'])
            distros.append(dict(id=item['Id'], etag=cfg['ETag'], arn=item['ARN'], config=cfg['DistributionConfig']))
    return distros

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--filters", type=str, nargs="+")
    parser.add_argument("--update", action="store_true", help="actually update CloudFront")
    return parser.parse_args()

if __name__ == "__main__":
    main()
