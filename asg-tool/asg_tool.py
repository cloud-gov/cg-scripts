#!/bin/env python3
import json
import subprocess
from urllib.parse import urlparse


def paginate_cf_curl(api_path, acc_resources=[], iteration=0):
    if iteration == 100:
        return acc_resources
    output = subprocess.run(
        [
            "cf",
            "curl",
            api_path,
        ],
        capture_output=True,
        check=True,
    )

    results = json.loads(output.stdout)
    pagination = results["pagination"]
    next_page = pagination["next"]
    resources = results["resources"]
    joined_resources = acc_resources + resources

    if next_page:
        parsed_api = urlparse(next_page["href"])
        next_path = f"{parsed_api.path}?{parsed_api.query}"
        return paginate_cf_curl(
            next_path, acc_resources=joined_resources, iteration=iteration + 1
        )
    else:
        return joined_resources


def get_spaces():
    resources = paginate_cf_curl("/v3/spaces?per_page=10")

    return resources


def bind_asg(asg_name: str):
    results = [asg_name]
    return results
