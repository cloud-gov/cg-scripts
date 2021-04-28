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
    Runs the script to print a header row (unless excluded) and outputs the
    records.
    """

    args = get_args()

    service_instances = get_service_instances(
        args.limit,
        args.exclude_federalist,
        args.federalist_only
    )

    # Print out a header row if it's not set to be excluded.
    if not args.exclude_header:
        print(
            "Broker Name,Service Plan Name,Organization Name,Space Name,Broker Instance Name,Creation Date,Is Federalist,Fiscal Year"
        )

    output_instances(service_instances)


def get_args():
    """
    Configures and parses all of the arguments passed into the script.
    """

    parser = argparse.ArgumentParser(description=description)

    parser.add_argument(
        "--exclude-federalist",
        action="store_true",
        default=False,
        help="Excludes Federalist service instances from the results; overridden by --federalist-only flag"
    )
    parser.add_argument(
        "--exclude-header",
        action="store_true",
        default=False,
        help="Excludes the header row from the output"
    )
    parser.add_argument(
        "--federalist-only",
        action="store_true",
        default=False,
        help="Only include Federalist service instances in the results; overrides --exclude-federaist flag"
    )
    parser.add_argument(
        "--limit",
        default=0,
        help="Only process the specified amount of records",
        type=int
    )

    return parser.parse_args()


def get_service_instances(
    limit=0,
    exclude_federalist=False,
    federalist_only=False
):
    """
    Retrieves all service instances that are associated with a domain configured
    in the platform.
    """

    service_instances = []
    resources_parsed = 0
    resources_skipped = 0

    page = CF_SERVICE_INSTANCES_API_URI

    # Check if we're only retrieving Federalist records; if so, add a query
    # parameter to the URI to help filter for them.
    # TODO once the CF API supports it: add support for excluding Federalist
    # service instances from the API call itself.
    # http://v3-apidocs.cloudfoundry.org/version/3.99.0/#filters
    if federalist_only:
        federalist_org_guid = subprocess.check_output(
            ["cf", "org", FEDERALIST_ORG_NAME, "--guid"]
        ).decode("utf-8").replace("\n", "")

        page = page + "&organization_guids=" + federalist_org_guid

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

            service_instance = parse_resource(resource)

            # Check to see if we should skip this record because of the
            # exclusion flags set.  If we skip, don't increase the counter so
            # that we're still able to retrieve the full amount of records
            # requested.
            # Note that if federalist_only was set, the records have already
            # been filtered to be just Federalist with the API call itself, and
            # they are returned regardless if exclude_federalist was set.
            if service_instance["org_name"] == FEDERALIST_ORG_NAME:
                if exclude_federalist and not federalist_only:
                    logger.warning("    ...Skipping {0} (Federalist)...".format(
                        service_instance["instance_name"]
                    ))
                    resources_skipped = resources_skipped + 1
                    continue
                else:
                    service_instance["is_federalist"] = "Yes"
            else:
                service_instance["is_federalist"] = "No"

            # Get the fiscal year for the instance.
            service_instance["fiscal_year"] = get_fiscal_year(
                service_instance["created_at"]
            )

            service_instances.append(service_instance)
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
            logger.info("...Finished processing {0} records ({1} skipped).".format(
                len(service_instances),
                resources_skipped
            ))

    return service_instances


def parse_resource(resource):
    """
    Takes in a CF API service instance resource and parses the following
    information out of it:

    - The broker name that manages the service instance
    - The service plan name that was used with the broker
    - The name associated with the service instance
    - The created at date of the service instance
    - The space name that the service instance resides in
    - The organization name that the service instance resides in
    """

    logger.info("    ...Parsing {0} ({1})...".format(
        resource["name"],
        resource["created_at"].split("T")[0]
    ))

    # Start by pulling out the service instance information directly.
    resource_info = {}
    resource_info["instance_name"] = resource["name"]
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


def get_fiscal_year(date_string):
    """
    Figures out and returns the fiscal year label based on a provided calendar
    date.
    """

    year, month, day = date_string.split("-")
    new_fiscal_year_months = ["10", "11", "12"]
    fiscal_year = int(year[2:])

    # Fiscal years start on October 1.
    if month in new_fiscal_year_months:
        fiscal_year = fiscal_year + 1

    return "FY{0}".format(fiscal_year)


def output_instances(service_instances):
    """
    Outputs a list of the processed service instances in CSV format.
    """

    for instance in service_instances:
        output = "{0},{1},{2},{3},{4},{5},{6},{7}".format(
            instance["broker"],
            instance["service_plan"],
            instance["org_name"],
            instance["space_name"],
            instance["instance_name"],
            instance["created_at"],
            instance["is_federalist"],
            instance["fiscal_year"]
        )

        print(output)


if __name__ == "__main__":
    main()
