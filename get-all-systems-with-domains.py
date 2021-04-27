#!/usr/bin/env python

"""
Script to provide a listing of all domains found within the system, paired with
the org and space names they belong to.

NOTE:  This script assumes you are logged into CF on the command line.
"""

import csv
import json
import subprocess

from urllib import error, request


CF_SERVICE_INSTANCES_API_URI = "/v3/service_instances?service_plan_names=cdn-route,custom-domain,domain,domain-with-cdn&order_by=created_at"
CF_SPACES_API_URI = "/v3/spaces/"
CF_ORGANIZATIONS_API_URI = "/v3/organizations/"


def get_all_instances():
    service_instances = []

    page = CF_SERVICE_INSTANCES_API_URI

    print("Beginning API processing...")

    while page is not None:
        try:
            output = json.loads(subprocess.check_output(["cf", "curl", page]).decode("utf-8"))

            for resource in output['resources']:
                print("    ...Processing {0} ({1})...".format(resource["name"], resource["created_at"].split("T")[0]))

                resource_info = {}
                resource_info["service_plan_guid"] = resource["relationships"]["service_plan"]["data"]["guid"]
                resource_info["domain_name"] = resource["name"]
                resource_info["created_at"] = resource["created_at"].split("T")[0]

                space_guid = resource["relationships"]["space"]["data"]["guid"]
                space_output = json.loads(subprocess.check_output(["cf", "curl", CF_SPACES_API_URI + space_guid]).decode("utf-8"))

                resource_info["space_name"] = space_output["name"]

                org_guid = space_output["relationships"]["organization"]["data"]["guid"]
                org_output = json.loads(subprocess.check_output(["cf", "curl", CF_ORGANIZATIONS_API_URI + org_guid]).decode("utf-8"))

                resource_info["org_name"] = org_output["name"]

                service_instances.append(resource_info)

            page = output["pagination"].get("next")

            if page is not None:
                uri_parts = page["href"].split("/")
                page = "{0}/{1}".format(uri_parts[-2], uri_parts[-1])
                print("...Processing next page...")
            else:
                print("...Finished processing.")
        except subprocess.CalledProcessError as exc:
            print("Unable to execute cf curl: {0}".format(exc))

    return service_instances


if __name__ == "__main__":
    service_instances = get_all_instances()

    for instance in service_instances:
        output = "{0},{1},{2},{3},{4}".format(
            instance["service_plan_guid"],
            instance["org_name"],
            instance["space_name"],
            instance["domain_name"],
            instance["created_at"]
        )

        print(output)
