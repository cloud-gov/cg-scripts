#!/usr/bin/env python3

import argparse
import csv
import functools
import json
import subprocess


def parse_args():
    """
    Parses command line arguments to run the script.
    """

    parser = argparse.ArgumentParser(
        description="Processes AWS API data of brokered services for cost analysis."
    )

    parser.add_argument(
        "aws_service",
        choices=["es", "rds", "redis"],
        help="The AWS service to analyze"
    )
    parser.add_argument(
        "json_file",
        help="The JSON output to process"
    )
    return parser.parse_args()


def analyze_es(json_file):
    """
    Analyzes a JSON file containing AWS Elasticsearch domain information.
    """

    print("Not implemented.")


def analyze_rds(json_file):
    """
    Analyzes a JSON file containing AWS RDS instance information.
    """

    @functools.cache
    def get_cf_entity_name(entity, guid):
        """
        Retrieves the name of a CF entity from a GUID.
        """

        cf_json = subprocess.check_output(
            ["cf", "curl", "/v3/" + entity + "/" + guid],
            universal_newlines=True
        )
        cf_data = json.loads(cf_json)

        return cf_data.get("name", "N/A")

    rds_instance_data = json.load(open(json_file))

    print("Instance Class,Engine,MultiAZ,Storage Type,Storage Size,Instance GUID,Space GUID,Organization GUID,Space Name,Organization Name")

    for db_instance in rds_instance_data["DBInstances"]:
        # Retrieve all of the tags associated with the instance.
        tags = { tag.get("Key"): tag.get("Value") for tag in db_instance["TagList"] }

        # Check if the instance has the appropriate CF metadata associated with
        # it.  This may not always represent a customer instance, but it's a
        # close enough estimate for our purposes.
        if "Instance GUID" in tags:
            org_name = get_cf_entity_name(
                "organizations",
                tags["Organization GUID"]
            )

            space_name = get_cf_entity_name(
                "spaces",
                tags["Space GUID"]
            )

            output = "{instance_class},{engine},{multi_az},{storage_type},{storage_size},{instance_guid},{space_guid},{org_guid},{space_name},{org_name}".format(
                instance_class=db_instance["DBInstanceClass"],
                engine=db_instance["Engine"],
                multi_az=db_instance["MultiAZ"] and "Yes" or "No",
                storage_type=db_instance["StorageType"],
                storage_size=db_instance["AllocatedStorage"],
                instance_guid=tags["Instance GUID"],
                space_guid=tags["Space GUID"],
                org_guid=tags["Organization GUID"],
                space_name=space_name,
                org_name=org_name
            )

            print(output)


def analyze_redis(json_file):
    """
    Analyzes a JSON file containing AWS ElastiCache Redis cluster information.
    """

    print("Not implemented.")


def main():
    args = parse_args()

    if args.aws_service == "es":
        analyze_es(args.json_file)
    elif args.aws_service == "rds":
        analyze_rds(args.json_file)
    elif args.aws_service == "redis":
        analyze_redis(args.json_file)
    else:
        print("Unknown command, exiting.")


if __name__ == "__main__":
    main()
