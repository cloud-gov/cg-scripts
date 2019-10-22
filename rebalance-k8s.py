#!/usr/bin/env python3
"""
Reschedule pods in kubernetes to balance load across minions.
"""
import argparse
import json
import logging
from random import sample
import subprocess
from time import sleep

logging.basicConfig(level=logging.INFO)

# basic workflow:
#  get all the replicasets
#  filter down to replicasets where all the replicas are healthy, and optionally where the replicaset has more than one replica
#  get all the pods
#  filter to just pods that are members of the filtered replicaset list
#  delete pods, one at a time, pausing between deletions
def main():
    args = parse_args()
    replicasets = get_all_replicasets(args.kubectl)
    logging.info("found %s replicasets", len(replicasets))
    pods = get_all_pods(args.kubectl)
    logging.info("found %s pods", len(pods))
    ha_replicasets = filter_replicasets(replicasets, args.ha_only)
    logging.info("found %s replicasets eligible for rescheduling", len(ha_replicasets))
    reschedule_size = 0
    if args.percent:
        reschedule_size = int(len(pods) * args.percent / 100)
    elif args.count:
        reschedule_size = args.count
    logging.info("will reschedule %s pods", reschedule_size)
    replicaset_names = {rs['metadata']['name'] for rs in ha_replicasets}
    pods_eligible_for_rescheduling = [pod for pod in pods if len(pod.get('metadata', {}).get("ownerReferences",[])) and pod['metadata']['ownerReferences'][0]["name"] in replicaset_names]
    logging.info("found %s pods eligible for rescheduling", len(pods_eligible_for_rescheduling))
    to_reschedule = sample(pods_eligible_for_rescheduling, reschedule_size)

    # sort by uid for some randomness. Otherwise, these are sorted by name, putting members of the same service together
    to_reschedule.sort(key=lambda x: x['metadata']['uid'])
    for pod in to_reschedule:
        relocate_pod(pod, args.kubectl)
        sleep(10)


def get_all_replicasets(kubectl: str = "kubectl"):
    """
    get all the replicasets that exist
    """
    out = subprocess.run([kubectl, 'get', 'replicasets', '-o', 'json'], check=True, text=True, capture_output=True)
    out = json.loads(out.stdout)
    return out['items']

def filter_replicasets(replicasets: list, ha_only: bool):
    """
    Filter replicasets to ones with more than one replica and where all the replicas are ready
    """
    min_replicas = 1
    if ha_only:
        min_replicas = 2
    return [rs for rs in replicasets if rs['spec'].get('replicas') == rs['status'].get('readyReplicas', 0) and rs['spec'].get('replicas', 0) >= min_replicas]


def get_all_pods(kubectl: str = "kubectl"):
    """
    get all the pods
    """
    out = subprocess.run([kubectl, 'get', 'pods', '-o', 'json'], check=True, text=True, capture_output=True)
    out = json.loads(out.stdout)
    return out['items'] 


def parse_args():
    parser = argparse.ArgumentParser()
    quantity = parser.add_mutually_exclusive_group(required=True)
    quantity.add_argument('--percent', '-p', type=int, help="percent of pods to reschedule")
    quantity.add_argument('--count', '-c', type=int, help="number of pods to reschedule")
    parser.add_argument('--kubectl', '-k', default='kubectl', help="path to kubectl binary. Leave unset if kubectl is on your PATH")
    parser.add_argument('--ha-only', action='store_true', help="only reschedule pods with replicas")
    return parser.parse_args()


def relocate_pod(pod, kubectl):
    pod_name = pod['metadata']['name']
    out = subprocess.run([kubectl, 'delete', 'pod', pod_name], check=True, text=True)


if __name__ == "__main__":
    main()
