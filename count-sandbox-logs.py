#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Count router logs per org per sandbox per month over the last three months.
"""

import sys
import os
import csv
import datetime

import requests
from dateutil import relativedelta

token = ''
api = "https://api.fr.cloud.gov"

def capiGet(token, server, path):
    """Issue GET request to api with bearer token"""
    headers = {'Authorization': 'bearer %s' % token}
    r = requests.get(server + path, headers=headers)
    r.raise_for_status()
    return r.json()

def capiGetWithNextUrl(next_url):
    """Retrieve resources from API endpoint with multiple calls using next_url"""
    resources = []
    while True:
        resp = capiGet(token, api, next_url)
        if resp.get('resources'):
            resources += resp['resources']
            if resp.get('next_url'):
                next_url = resp['next_url']
            else:
                break
        else:
            break
    return resources

def cfGetOrgs():
    """Retrieve map containing sandbox organizations"""
    orgs = {}
    next_url = '/v2/organizations?q=name>sandbox&q=name<sandboy&order-direction=asc&results-per-page=50'
    resources = capiGetWithNextUrl(next_url)
    for entry in resources:
        orgs[entry['entity']['name']] = entry['metadata']['guid']

    return orgs

def cfGetOrgsAndSpaces(orgs):
    """Retrieve map containing sandbox organizations and spaces"""
    orgsWithSpaces = {}
    for org in orgs:
        orgsWithSpaces[org] = {}
        orgsWithSpaces[org]['guid'] = orgs[org]
        orgsWithSpaces[org]['spaces'] = {}
        next_url = '/v2/organizations/' + orgs[org] + '/spaces?results-per-page=50'
        resources = capiGetWithNextUrl(next_url)
        for entry in resources:
            orgsWithSpaces[org]['spaces'][entry['entity']['name']] = entry['metadata']['guid']

    return orgsWithSpaces

def cfGetSpaceEvents(orgGuid, spaceGuid):
    events = []
    next_url = '/v2/events?q=organization_guid:' + orgGuid + '&space_guid:' + spaceGuid
    resources = capiGetWithNextUrl(next_url)
    for entry in resources:
        entity = entry["entity"]

        if entity["type"] == "audit.app.build.create":
            events.append(entity["actor_name"] + " pushed a app called " + entity["actee_name"] + " on " + entity["timestamp"])

    return "\n".join(events)

def getElasticSearchResults():
    query = {
        'size': 0,
        'query': {
            'bool': {
                'must': [
                    {
                        'prefix': {
                            '@cf.org': 'sandbox-'
                        }
                    },
                    {
                        'term': {
                            '@source.type': 'RTR'
                        }
                    }
                ]
            }
        },
        'aggs': {
            'count': {
                'terms': {
                    'field': '@cf.org',
                    'size': 999
                },
                'aggs': {
                    'count': {
                        'terms': {
                            'field': '@cf.space',
                            'size': '999'
                        },
                        'aggs': {
                            'count': {
                                'date_histogram': {
                                    'field': '@timestamp',
                                    'interval': 'month'
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    today = datetime.date.today()
    first = datetime.date(today.year, today.month, 1)
    indices = [
        (first - relativedelta.relativedelta(months=idx)).strftime('logs-app-%Y.%m.*')
        for idx in reversed(range(3))
    ]
    months = [
        (first - relativedelta.relativedelta(months=idx)).strftime('%Y-%m-%d')
        for idx in reversed(range(3))
    ]

    result = requests.get(
        'http://{}:9200/{}/_search'.format(os.environ['ES_HOST'], ','.join(indices)),
        json=query,
    ).json()

    return result, months

def getCSVRows(esResult, orgsAndSpaces):
    rows = []
    for org_bucket in esResult['aggregations']['count']['buckets']:
        org = org_bucket['key']
        for space_bucket in org_bucket['count']['buckets']:
            space = space_bucket['key']
            row = {
                'org': org,
                'space': space,
                'events': cfGetSpaceEvents(orgsAndSpaces[org]['guid'], orgsAndSpaces[org]['spaces'][space])
            }

            for month_bucket in space_bucket['count']['buckets']:
                month = month_bucket['key_as_string']
                row[month.split('T')[0]] = month_bucket['doc_count']
            rows.append(row)
    return rows

def writeCSV(rows, months, filename='summary.csv'):
    with open(filename, 'w') as fp:
        writer = csv.DictWriter(fp, fieldnames=['org', 'space', 'events'] + months)
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    if (not os.getenv("ES_HOST")):
        print('ES_HOST for application log retrieval is required.\nEx: 127.0.0.1\n')
        sys.exit(255)
    if (not os.getenv("CF_BEARER_TOKEN")):
        print('CF_BEARER_TOKEN is required to connect to the CloudFoundry API')
        sys.exit(255)
    else:
        token = os.environ['CF_BEARER_TOKEN']

    orgs              = cfGetOrgs()
    orgsAndSpaces     = cfGetOrgsAndSpaces(orgs)
    esResults, months = getElasticSearchResults()
    rows              = getCSVRows(esResults, orgsAndSpaces)
    writeCSV(rows, months)


