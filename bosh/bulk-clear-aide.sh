#!/bin/bash
#
# This script does a bulk reset of aide across all VMs in all deployments

set -e

for DEPLOYMENTS in $(bosh deps --json | jq -r '.Tables[].Rows[].name')
do
    for INSTANCEGROUP in $(bosh -d $DEPLOYMENTS vms --json | jq -r '.Tables[].Rows[].instance' | awk -F'/' '{print $1}' | sort | uniq)
    do
        echo "Deployment: $DEPLOYMENTS InstanceGroup: $INSTANCEGROUP"
        bosh -d $DEPLOYMENTS ssh $INSTANCEGROUP "sudo /var/vcap/jobs/aide/bin/post-deploy; sudo /etc/cron.hourly/run-report"
    done
done