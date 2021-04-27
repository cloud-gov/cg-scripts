#!/usr/bin/env python

description = """
Script that provides a listing of all domains found within the system, paired
with the org and space names they belong to and a bit of other metadata.  The
output is sorted in chronological order by created_at date.

NOTE:  This script assumes you are logged into CF on the command line as it
makes use of calls with the cf CLI.
"""

import argparse
import json
import logging
import subprocess

# CF API URI endpoint configuration.
CF_SERVICE_INSTANCES_API_URI = "/v3/service_instances?service_plan_names=cdn-route,custom-domain,domain,domain-with-cdn&order_by=created_at"
CF_SPACES_API_URI = "/v3/spaces/"
CF_ORGANIZATIONS_API_URI = "/v3/organizations/"
CF_SERVICE_PLANS_API_URI = "/v3/service_plans/"
CF_SERVICE_OFFERINGS_API_URI = "/v3/service_offerings/"


# Federalist organization name.
FEDERALIST_ORG_NAME = "gsa-18f-federalist"


# Logging configuration - this will output logs to the console/STDOUT/STDERR.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def main():
    """
    Runs the script.
    """

    args = get_args()

    service_instances = get_all_instances(args.limit)
    num_records = len(service_instances)

    # Check to see if we should keep cloud.gov and Federalist domains together
    # or make them separate and output the results.
    if not args.split:
        print("\n----- CSV OUTPUT ({0} TOTAL RECORDS) -----\n".format(
            num_records
        ))
        output_instances(service_instances)
    else:
        print("\n----- CSV OUTPUT - SPLIT DOMAINS ({0} TOTAL RECORDS) -----".format(
            num_records
        ))
        output_split_instances(service_instances)


def get_args():
    """
    Configures and parses all of the arguments passed into the script.
    """

    parser = argparse.ArgumentParser(description=description)

    parser.add_argument(
        "--limit",
        default=0,
        help="Only process this amount of records",
        type=int)
    parser.add_argument(
        "--split",
        action="store_true",
        default=False,
        help="Split records between cloud.gov and Federalist domains"
    )

    return parser.parse_args()


def get_all_instances(limit=0):
    """
    Retrieves all service instances that are associated with a domain configured
    in the platform.
    """

    service_instances = []
    resources_parsed = 0

    page = CF_SERVICE_INSTANCES_API_URI

    # If limit is set, display an extra message to remind the operator.
    if limit > 0:
        logger.info("Beginning API processing (limiting to {0} records)...".format(
            limit
        ))
    else:
        logger.info("Beginning API processing...")

    while page is not None:
        try:
            output = json.loads(subprocess.check_output(["cf", "curl", page]).decode("utf-8"))
        except subprocess.CalledProcessError as exc:
            logger.error("Unable to execute cf curl: {0}".format(exc))
            break

        # Go through each resource returned and parse all of the relevant
        # information we need.
        for resource in output['resources']:
            # Check to see if we've already hit the resource limit set when the
            # script was invoked.
            if limit > 0 and resources_parsed >= limit:
                break

            service_instances.append(parse_resource(resource))
            resources_parsed = resources_parsed + 1

        # Check to see if we've hit the limit of the amount of records we want
        # to process.
        if limit > 0 and resources_parsed < limit:
            page = output["pagination"].get("next")
        else:
            page = None

        # If we still have a page value, we need to retrieve the piece to get to
        # the next page.
        if page is not None:
            uri_parts = page["href"].split("/")
            page = "{0}/{1}".format(uri_parts[-2], uri_parts[-1])
            logger.info("...Processing next page...")
        else:
            logger.info("...Finished processing.")

    return service_instances


def parse_resource(resource):
    """
    Takes in a CF API service instance resource and parses the following
    information out of it:

    - The broker name that manages the service instance
    - The service plan name that was used with the broker
    - The domain name associated with the service instance
    - The created at date
    - The space name that the service instance resides in
    - The organization name that the service instance resides in
    """

    logger.info("    ...Parsing {0} ({1})...".format(
        resource["name"],
        resource["created_at"].split("T")[0]
    ))

    # Start pulling out the service instance information directly.
    resource_info = {}
    resource_info["domain_name"] = resource["name"]
    resource_info["created_at"] = resource["created_at"].split("T")[0]

    # Retrieve the service plan information.
    service_plan_guid = resource["relationships"]["service_plan"]["data"]["guid"]
    service_plan_output = json.loads(subprocess.check_output(["cf", "curl", CF_SERVICE_PLANS_API_URI + service_plan_guid]).decode("utf-8"))
    resource_info["service_plan"] = service_plan_output["name"]

    # Retrieve the broker information.
    service_offering_guid = service_plan_output["relationships"]["service_offering"]["data"]["guid"]
    service_offering_output = json.loads(subprocess.check_output(["cf", "curl", CF_SERVICE_OFFERINGS_API_URI + service_offering_guid]).decode("utf-8"))
    resource_info["broker"] = service_offering_output["name"]

    # Retrieve the space information.
    space_guid = resource["relationships"]["space"]["data"]["guid"]
    space_output = json.loads(subprocess.check_output(["cf", "curl", CF_SPACES_API_URI + space_guid]).decode("utf-8"))
    resource_info["space_name"] = space_output["name"]

    # Retrieve the organization information.
    org_guid = space_output["relationships"]["organization"]["data"]["guid"]
    org_output = json.loads(subprocess.check_output(["cf", "curl", CF_ORGANIZATIONS_API_URI + org_guid]).decode("utf-8"))
    resource_info["org_name"] = org_output["name"]

    return resource_info


def output_instances(service_instances):
    """
    Outputs a list of the processed service instances in CSV format.
    """

    for instance in service_instances:
        output = "{0},{1},{2},{3},{4},{5}".format(
            instance["broker"],
            instance["service_plan"],
            instance["org_name"],
            instance["space_name"],
            instance["domain_name"],
            instance["created_at"]
        )

        print(output)


def output_split_instances(service_instances):
    """
    Splits a list of service instances into two separate lists, one for
    cloud.gov domains and one for Federalist domains, and outputs the results
    seperately.
    """

    # Split out cloud.gov-only domains.
    cloud_instances = [
        instance for instance in service_instances
        if instance["org_name"] != FEDERALIST_ORG_NAME
    ]

    # Split out Federalist-only domains.
    federalist_instances = [
        instance for instance in service_instances
        if instance["org_name"] == FEDERALIST_ORG_NAME
    ]

    # Print out the two separate lists.
    print("\ncloud.gov-only domains ({0} records):\n".format(
        len(cloud_instances)
    ))
    output_instances(cloud_instances)
    print("\nFederalist-only domains ({0} records):\n".format(
        len(federalist_instances)
    ))
    output_instances(federalist_instances)


if __name__ == "__main__":
    main()
