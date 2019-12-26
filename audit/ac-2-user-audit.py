#!/usr/bin/env python3
import argparse
import csv
import datetime
import subprocess
import sys
import yaml


def make_date(datestr):
    return datetime.datetime(*[int(x) for x in datestr.split('-')])


# https://stackoverflow.com/a/24448716/4949938
def flatten(current, key, result):
    if isinstance(current, dict):
        for k in current:
            new_key = "{0}.{1}".format(key, k) if len(key) > 0 else k
            flatten(current[k], new_key, result)
    else:
        result[key] = current
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Show a list of users in UAA."
    )
    parser.add_argument(
        'since',
        help="Return users created on or after this date YYYY-MM-DD",
        type=make_date
    )

    args = parser.parse_args()

    try:
        data = yaml.safe_load(subprocess.check_output(["uaa", "list-users"]))
    except subprocess.CalledProcessError as exc:
        parser.error(
            """
            Unable to list UAA users:{}
            Request a token with: go-uaac get-client-credentials-token admin -s ''
            """.format(exc.output)
        )

    results = []
    for user in data:
        res = {}
        flatten(user, "", res)

        for idx, group in enumerate(res["groups"]):
            flatten(group, "group_{0}".format(idx), res)
        del(res["groups"])

        for idx, group in enumerate(res["emails"]):
            flatten(group, "email_{0}".format(idx), res)
        del(res["emails"])

        results.append(res)

    writer = csv.DictWriter(
        sys.stdout,
        fieldnames=results[0].keys(),
        extrasaction='ignore',
        dialect='excel'
    )

    writer.writeheader()

    for user in results:
        # 2019-12-17T19:00:15.076Z
        created_date = datetime.datetime.strptime(user["meta.created"], "%Y-%m-%dT%H:%M:%S.%fZ")
        if created_date >= args.since:
            writer.writerow(user)
