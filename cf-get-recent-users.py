#!/usr/bin/env python

import argparse
import csv
import datetime
from email.utils import parseaddr
import subprocess
import sys
import yaml


def make_date(datestr):
    return datetime.datetime(*[int(x) for x in datestr.split('-')])

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
        check = yaml.safe_load(subprocess.check_output(
            [
                'uaac',
                'users',
                '--attributes',
                'username',
                '--count',
                '1'
            ]
        ))
        total = check['totalresults']
        data = yaml.safe_load(subprocess.check_output(
            [
                'uaac',
                'users',
                '--attributes',
                'username',
                '--attributes',
                'meta.created',
                '--attributes',
                'verified',
                '--count',
                str(total)
            ]
        ))
        assert data['itemsperpage'] == total
    except subprocess.CalledProcessError as exc:
        parser.error(
            """
            Unable to list UAA users:{}
            Request a token with: uaac token sso get cf -s '' --scope scim.read
            """.format(exc.output)
        )
    except AssertionError:
        parser.error(
            "UAA returned a truncated response. Time to implement paging :("")"
        )

writer = csv.DictWriter(
    sys.stdout,
    fieldnames=['username', 'meta.created'],
    extrasaction='ignore',
    dialect='excel-tab'
)
writer.writeheader()
for user in data['resources']:
    email_address = parseaddr(user['username'])[1]
    if '@' in email_address and user['meta.created'] >= args.since:
        writer.writerow(user)
