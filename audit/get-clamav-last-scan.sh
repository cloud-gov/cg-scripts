#!/bin/bash

for deployment in $(bosh deployments --json | jq -r '.Tables[].Rows[].name')
do
    echo "Working deployment: $deployment"
    bosh -d $deployment ssh --results --column=Instance --column=Stdout -c "sudo tail /var/vcap/sys/log/clamav/sched.log | grep 'End Date'"
done
