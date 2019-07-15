#!/usr/bin/env python3

import argparse
import json
import logging
import subprocess
import urllib


def main():

    args = get_args()

    queries = []
    if args.after:
        queries.append(f'q=timestamp>{args.after}')
    if args.before:
        queries.append(f'q=timestamp<{args.before}')
    initial_request = f'/v2/events?{"&".join(queries)}'
    logging.info('getting %s', initial_request)
    cf_out = subprocess.check_output(['cf', 'curl', initial_request], universal_newlines=True)
    cf_out = json.loads(cf_out)
    if args.user:
        events = [event for event in cf_out['resources'] if event['entity']['actor'] == args.user]
    else:
        events = cf_out['resources']
    next_url = cf_out['next_url']
    while next_url is not None:
        logging.info('getting %s', next_url)
        cf_out = subprocess.check_output(['cf', 'curl', next_url], universal_newlines=True)
        cf_out = json.loads(cf_out)
        if args.user:
            resources = [event for event in cf_out['resources'] if event['entity']['actor'] == args.user]
        else:
            resources = cf_out['resources']
        events.extend(resources)
        next_url = cf_out['next_url']
    
    print(json.dumps(events))
        

def get_args():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(
        description="Get cloudfoundry events by time and/or user"
    )
    parser.add_argument('--after', help="find events after this timestamp (timestamp should be ISO8601)")
    parser.add_argument('--before', help="find events before this timestamp (timestamp should be ISO8601)")
    parser.add_argument('--user', help='find events for this user')
    return parser.parse_args()

if __name__ == '__main__':
    main()
