#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Count router logs per org per sandbox per month over the last three months.
"""

import os
import csv
import datetime

import requests
from dateutil import relativedelta

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
    (first - relativedelta.relativedelta(months=idx)).strftime('logs-app-%y.%m.*')
    for idx in reversed(range(3))
]
months = [
    (first - relativedelta.relativedelta(months=idx)).strftime('%y-%m-%d')
    for idx in reversed(range(3))
]

result = requests.get(
    'http://{}:9200/{}/_search'.format(os.environ['ES_HOST'], ','.join(indices)),
    json=query,
).json()

rows = []
for org_bucket in result['aggregations']['count']['buckets']:
    org = org_bucket['key']
    for space_bucket in org_bucket['count']['buckets']:
        space = space_bucket['key']
        row = {
            'org': org,
            'space': space,
        }
        for month_bucket in space_bucket['count']['buckets']:
            month = month_bucket['key_as_string']
            row[month.split('T')[0]] = month_bucket['doc_count']
        rows.append(row)

with open('summary.csv', 'w') as fp:
    writer = csv.DictWriter(fp, fieldnames=['org', 'space'] + months)
    writer.writeheader()
    writer.writerows(rows)
