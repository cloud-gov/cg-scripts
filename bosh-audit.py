#!/usr/bin/env python3

import argparse
import json
import subprocess


def main():
    args = get_args()
    
    bosh_call = ['bosh', 'events', '--json']
    if args.after:
        bosh_call.extend(['--after', args.after])
    if args.before:
        bosh_call.extend(['--before', args.before])
    if args.user:
        bosh_call.extend(['--args.user'])
    process_out = subprocess.check_output(bosh_call, universal_newlines=True)
    out = json.loads(process_out)
    events = out['Tables'][0]['Rows']

    # sometimes the id field looks like 3 -> 1
    # in these cases, we want 3
    last_id = events[-1]['id'].split(' ')[0]
    last_last_id = None

    while True:
        if last_id == last_last_id:
            break
        last_last_id = last_id
        process_out = subprocess.check_output(bosh_call + ['--before-id', last_id], universal_newlines=True)
        out = json.loads(process_out)
        events.extend(out['Tables'][0]['Rows'])
        # sometimes the id field looks like 3 -> 1
        # in these cases, we want 3
        last_id = events[-1]['id'].split(' ')[0]

    print(json.dumps(events))


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--after', help="find events after this timestamp (ex: 2019-12-31 13:55")
    parser.add_argument('--before', help="find events before this timestamp (ex: 2019-12-31 13:55")
    parser.add_argument('--user', help="find events for this user")
    return parser.parse_args()

if __name__ == '__main__':
    main()
