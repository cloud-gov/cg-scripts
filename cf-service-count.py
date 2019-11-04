#! /usr/bin/env python3
import argparse
import json
import logging
import subprocess
import pandas as pd


def main():
    args = arggies()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    service_instances = []
    service_map = {"service_instance_name": [],
                   "service_offering": [],
                   "service_plan": [],
                   "org": [],
                   "space": []
                   }

    logging.info("beginning fetch.")
    cf_out = subprocess.run(['cf', 'curl', "/v2/service_instances"], shell=False, stdout=subprocess.PIPE)
    si_data = json.loads(cf_out.stdout)
    service_instances.extend(si_data["resources"])
    next_url = si_data["next_url"]
    while next_url is not None:
        logging.debug("fetching page {0}".format(next_url))

        cf_out = subprocess.run(['cf', 'curl', next_url], shell=False, stdout=subprocess.PIPE)
        si_data = json.loads(cf_out.stdout)
        service_instances.extend(si_data["resources"])
        next_url = si_data["next_url"]

    logging.info("there are {0} service instances, this is going to take awhile".format(len(service_instances)))

    # this is so inefficient it hurts but it has to be serial. therefore I wrote an egregiously primitive cache.
    # serialise the cf cli call to a string, store it as the key, store the response to it.
    # if the serialised cf cli call exists as a dict key, therefore it's response will be predetermined (since the resp
    # data can't change - deletions don't count) and we can use the predetermined response.
    cache = {}
    cache_hits = 0
    cache_misses = 0

    for si in service_instances:
        logging.info("operating on {0} of ".format(si["entity"]["name"]))
        service_map["service_instance_name"].append(si["entity"]["name"])

        logging.debug("fetching service info")
        cf_svc_call = ['cf', 'curl', si["entity"]["service_url"]]
        cf_svc_call_str = "".join(cf_svc_call)

        if cf_svc_call_str in cache:
            cache_hits += 1
            logging.debug("cache hit on {0}".format(cf_svc_call))
            service_map["service_offering"].append(cache[cf_svc_call_str]["entity"]["label"])
        else:
            cache_misses += 1
            logging.debug("cache miss on {0}".format(cf_svc_call))
            cache[cf_svc_call_str] = None
            cf_svc_url_out = subprocess.run(cf_svc_call, shell=False,
                                            stdout=subprocess.PIPE)
            cf_svc_url_data = json.loads(cf_svc_url_out.stdout)
            cache[cf_svc_call_str] = cf_svc_url_data
            service_map["service_offering"].append(cache[cf_svc_call_str]["entity"]["label"])

        logging.debug("fetching service plan info")
        cf_svc_plan_call = ['cf', 'curl', si["entity"]["service_plan_url"]]
        cf_svc_plan_call_str = "".join(cf_svc_plan_call)

        if cf_svc_plan_call_str in cache:
            cache_hits += 1
            logging.debug("cache hit on {0}".format(cf_svc_plan_call))
            service_map["service_plan"].append(cache[cf_svc_plan_call_str]["entity"]["name"])
        else:
            cache_misses += 1
            logging.debug("cache miss on {0}".format(cf_svc_plan_call))
            cache[cf_svc_plan_call_str] = None
            cf_svc_plan_out = subprocess.run(cf_svc_plan_call, shell=False, stdout=subprocess.PIPE)
            cache[cf_svc_plan_call_str] = json.loads(cf_svc_plan_out.stdout)
            service_map["service_plan"].append(cache[cf_svc_plan_call_str]["entity"]["name"])

        logging.debug("fetching space info")
        cf_space_call = ["cf", "curl", "/v3/spaces/{0}".format(si["entity"]["space_guid"])]
        cf_space_call_str = "".join(cf_space_call)

        if cf_space_call_str in cache:
            cache_hits += 1
            logging.debug("cache hit on {0}".format(cf_space_call))
            service_map["space"].append(cache[cf_space_call_str]["name"])
        else:
            cache_misses += 1
            logging.debug("cache miss on {0}".format(cf_space_call))
            cf_space_out = subprocess.run(cf_space_call, shell=False, stdout=subprocess.PIPE)
            cache[cf_space_call_str] = json.loads(cf_space_out.stdout)
            service_map["space"].append(cache[cf_space_call_str]["name"])

        logging.debug("fetching org info")
        # it's a full URL, and we need to split on it.
        # it's also guaranteed to be in the cache because of the previous call.
        org_link = "/" + "/".join(cache[cf_space_call_str]["links"]["organization"]["href"].split("/")[3:])
        cf_org_call = ['cf', 'curl', org_link]
        cf_org_call_str = "".join(cf_org_call)

        if cf_org_call_str in cache:
            cache_hits += 1
            logging.debug("cache hit on {0}".format(cf_org_call))
            service_map["org"].append(cache[cf_org_call_str]["name"])
        else:
            cache_misses += 1
            logging.debug("cache miss on {0}".format(cf_org_call))
            cf_org_out = subprocess.run(cf_org_call, shell=False, stdout=subprocess.PIPE)
            cache[cf_org_call_str] = json.loads(cf_org_out.stdout)
            service_map["org"].append(cache[cf_org_call_str]["name"])

    # this is just because it's easiest for the conversion to csv.
    df = pd.DataFrame(service_map)
    if args.file_name != "":
        df.to_csv(args.file_name, index=False)
    else:
        df.to_csv("service-count.csv", index=False)

    # about 300ms per network call on average
    logging.info("{0} cache hits, {1} cache misses, saved about {2:.2f}s by caching".format(
        cache_hits,
        cache_misses,
        0.3 * cache_hits,
    ))


def arggies():
    parser = argparse.ArgumentParser(description="Saves a CSV of the services customers have deployed.")
    parser.add_argument("--file-name", help="Name of the CSV file you want to save to.")
    parser.add_argument("--debug", help="Enable debug logging.", action="store_true")
    return parser.parse_args()


if __name__ == '__main__':
    main()
