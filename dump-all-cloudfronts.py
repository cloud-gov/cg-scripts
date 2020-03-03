import boto3
import json


def main():
    client = boto3.client('cloudfront')
    distros = get_all_distros(client)
    for distro in distros:
        with open(distro['Id'], 'x') as f:
            del(distro['LastModifiedTime'])
            json.dump(distro, f, indent=2)


def get_all_distros(client):
    distroresponse = client.list_distributions()
    distros = distroresponse['DistributionList']['Items']
    while distroresponse['DistributionList'].get("NextMarker"):
        distroresponse = client.list_distributions(Marker=distroresponse['DistributionList']['NextMarker'])
        distros.extend(distroresponse['DistributionList']['Items'])
    return distros


if __name__ == "__main__":
    main()
