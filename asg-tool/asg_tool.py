import json
import subprocess
from urllib.parse import urlparse


def filter_resource_item(item: dict) -> dict:
    guid = item["guid"]
    name = item["name"]

    if not guid or not name:
        return None

    updated_item = {"guid": guid, "name": name}

    return updated_item


def filter_resources(resources: list) -> list:
    filtered = []

    for item in resources:
        filtered_item = filter_resource_item(item)

        if filtered_item == None:
            continue

        filtered.append(filtered_item)

    return filtered


def cf_curl_results_handler(output: object):
    results = {}

    # Try to load output as JSON.
    try:
        results = json.loads(output.stdout)
    except:
        results = {}

    if hasattr(results, "__iter__") and "errors" in results:
        raise Exception(results)

    return results


def cf_curl_get(
    api_path: str,
    acc_resources: list = [],
    iteration: int = 0,
) -> list:
    if iteration == 100:
        return acc_resources

    command = ["cf", "curl", api_path]
    output = subprocess.run(command, capture_output=True, check=True, encoding="utf-8")

    results = cf_curl_results_handler(output)
    pagination = results["pagination"]
    next_page = pagination["next"]
    resources = results["resources"]
    joined_resources = acc_resources + resources

    if next_page:
        parsed_api = urlparse(next_page["href"])
        next_path = f"{parsed_api.path}?{parsed_api.query}"
        return cf_curl_get(
            next_path, acc_resources=joined_resources, iteration=iteration + 1
        )
    else:
        return joined_resources


def cf_curl_delete(
    api_path: str,
) -> list:
    command = ["cf", "curl", api_path, "-X", "DELETE"]
    output = subprocess.run(command, capture_output=True, check=True, encoding="utf-8")
    results = cf_curl_results_handler(output)
    return results


def cf_curl_post(
    api_path: str,
    data: dict,
) -> list:
    formatted = json.dumps(data)
    command = ["cf", "curl", api_path, "-X", "POST", "-d", formatted]
    output = subprocess.run(command, capture_output=True, check=True, encoding="utf-8")
    results = cf_curl_results_handler(output)
    return results["data"]


def get_spaces() -> list:
    resources = cf_curl_get("/v3/spaces?per_page=100")
    filtered = filter_resources(resources)

    return filtered


def get_asg_guid(asg_name: str) -> str:
    results = cf_curl_get(f"/v3/security_groups?names={asg_name}")
    pick_asg = list(filter(lambda asg: asg["name"] == asg_name, results))
    filtered = filter_resources(pick_asg)

    if len(filtered) < 1:
        return None

    guid = filtered[0]["guid"]
    return guid


def get_running_space_asgs(space_guid: str) -> list:
    resources = cf_curl_get(f"/v3/security_groups?running_space_guids={space_guid}")

    return resources


def setup_asg_action(asg_name: str) -> tuple:
    print("Getting space information")
    asg_guid = get_asg_guid(asg_name)

    if not asg_guid:
        raise ValueError(f"App security group named {asg_name} does not exist.")

    spaces = get_spaces()

    if len(spaces) < 1:
        raise ValueError("No spaces exist")

    return (asg_guid, spaces)


def bind_asg(asg_name: str) -> str:
    asg_guid, spaces = setup_asg_action(asg_name)

    print(f"Start binding security group {asg_name} to all spaces")
    for space in spaces:
        try:
            data = {"data": [space]}

            cf_curl_post(
                f"/v3/security_groups/{asg_guid}/relationships/running_spaces",
                data=data,
            )
            print(f'Bound {asg_name} to NAME: {space["name"]} - GUID: {space["guid"]}')
        except Exception as err:
            print(
                f'Unable to bind {asg_name} to NAME: {space["name"]} - GUID: {space["guid"]}'
            )
            print(str(err))

    return "Finished"


def check_spaces() -> list:
    print("Getting space information")
    results = []
    spaces = get_spaces()

    for space in spaces:
        space_guid = space["guid"]
        asg_resources = get_running_space_asgs(space_guid)
        filtered = filter_resources(asg_resources)
        updated_space = {
            "name": space["name"],
            "guid": space["guid"],
            "security_groups": filtered,
        }

        results.append(updated_space)

    return results


def unbind_asg(asg_name: str) -> str:
    asg_guid, spaces = setup_asg_action(asg_name)

    print(f"Start unbinding security group {asg_name} from all spaces")
    for space in spaces:
        try:
            space_guid = space["guid"]
            cf_curl_delete(
                f"/v3/security_groups/{asg_guid}/relationships/running_spaces/{space_guid}"
            )
            print(
                f'Unbound {asg_name} for NAME: {space["name"]} - GUID: {space["guid"]}'
            )
        except Exception as err:
            print(
                f'Unable to unbind {asg_name} for NAME: {space["name"]} - GUID: {space["guid"]}'
            )
            print(str(err))

    return "Finished"
