#!/bin/bash
#
# This script gets all `prometheus-*` deployments and using BOSH ssh monit restarts cf_exporter
# During CF deployments the exporter can timeout connecting to diego-api and does not re-attach
# So this script exists to quickly restart the service on all prometheus deployments

set -e
for OUTPUT in $(bosh deployments --json | jq -r ".Tables[].Rows[].name" | grep "prometheus")
do
    echo "Bouncing cf_exporter for $OUTPUT"
    bosh -d $OUTPUT ssh prometheus "sudo monit restart cf_exporter"
done
