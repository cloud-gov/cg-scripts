import json
import logging
import subprocess

#
# goal: produce a CSV with lines of:
# `Unique Asset Identifier` - can be any arbirtary name - we use the VM name
# IPv4 - hopefully obvious what this means
# IPv6 - we don't currently include this
# DNS name - not currently included
# NetBIOS name - not currently included
# MAC Address - not currently included
# Asset Weight - always 5
# Authenticated Scan - always 'Agent Based'
# Baseline Configuration Name - always Ubuntu Stemcell
# OS Name[ - e.g. Ubuntu
# OS Version - e.g. 14.04.1
# Location - Cloud Provider's Availability zone name
# Asset type - what it is (e.g. EC2)
# Virtual - is it a VM
# Public - is it public-internet-facing
# In latest scan - is it supposed to be in the latest scan (yes)
# Comment - optional comments
#

# call out the ones we don't use, so they're easier to replace if we do use them
# use empty string rather than None to make printing easier later
IPV6 = ""
DNS_NAME = ""
NETBIOS_NAME = ""
MAC_ADDR = ""
ASSET_WEIGHT = "5"
AUTH_SCAN = "Agent Based"
OS_NAME = "Ubuntu"
ASSET_TYPE = "EC2"
VIRTUAL = "Yes"
PUBLIC = "No"
IN_LATEST_SCAN = "Yes"
COMMENT = ""  # no comment


# map our az names to AWS's
bosh_az_to_aws_az = {"z1": "us-gov-west-1a", "z2": "us-gov-west-1b"}


def get_os_version_from_stemcell(stemcell):
    """Return the OS version for a stemcell name"""
    stemcell_name = stemcell["name"].lower()
    version = None
    # TODO: validate minor version, as it may change in the future
    if "xenial" in stemcell_name:
        version = "16.04.5"
    elif "trusty" in stemcell_name:
        version = "14.04.1"
    return version


def get_deployment_to_os_map():
    """Return a dict of deployment name to deployment stemcell name"""
    response = subprocess.check_output(["bosh", "curl", "/deployments"])
    deployments = json.loads(response)
    deployment_to_os = {}
    for deployment in deployments:
        versions = set()
        for stemcell in deployment["stemcells"]:
            version = get_os_version_from_stemcell(stemcell)
            if version is None:
                logging.warning("Could not determine version for %s", str(stemcell))
            versions.add(version)
            if len(versions) > 1:
                logging.warning( "more than one stemcell in use for %s - using first of %s", deployment["name"], str(versions))
        deployment_to_os[deployment["name"]] = list(versions)[0]
    return deployment_to_os


def get_inventory(deployment_to_os_version):
    """Return the rows that will actually make our inventory"""
    inventory = []
    for deployment, version in deployment_to_os_version.items():
        response = subprocess.check_output(
            ["bosh", "curl", "/deployments/{}/vms".format(deployment)]
        )
        vms = json.loads(response)
        for vm in vms:
            inventory.append(
                [
                    vm["job"],
                    vm["ips"][0],
                    IPV6,
                    DNS_NAME,
                    NETBIOS_NAME,
                    MAC_ADDR,
                    ASSET_WEIGHT,
                    AUTH_SCAN,
                    OS_NAME,
                    version,
                    bosh_az_to_aws_az[vm["az"]],
                    ASSET_TYPE,
                    VIRTUAL,
                    PUBLIC,
                    IN_LATEST_SCAN,
                    COMMENT,
                ]
            )
    return inventory


def main():
    deployment_to_os_version = get_deployment_to_os_map()
    inventory = get_inventory(deployment_to_os_version)
    for item in inventory:
        # N.B. if we fail to get the version, it will show up as the string 'None'
        print(",".join([str(element) for element in item]))


if __name__ == "__main__":
    main()
