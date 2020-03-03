import argparse
import json
import datetime
import time

import boto3

RESTRICTIONS = {
                "GeoRestriction": {
                    "RestrictionType": "whitelist",
                    "Quantity": 43,
                    "Items": [
                        "SI",
                        "UM",
                        "NL",
                        "MT",
                        "VI",
                        "FR",
                        "ES",
                        "RO",
                        "AQ",
                        "AU",
                        "AS",
                        "SE",
                        "FI",
                        "BG",
                        "DE",
                        "PR",
                        "SK",
                        "EE",
                        "LV",
                        "LU",
                        "KR",
                        "GU",
                        "LT",
                        "GB",
                        "GR",
                        "NZ",
                        "AT",
                        "CX",
                        "MX",
                        "JP",
                        "HU",
                        "MH",
                        "IE",
                        "PL",
                        "CA",
                        "PT",
                        "BE",
                        "DK",
                        "CZ",
                        "IT",
                        "CH",
                        "US",
                        "HR"
                    ]
                }
            }

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
            time.sleep(3)

    
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
