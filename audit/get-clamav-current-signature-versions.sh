#!/bin/bash

for deployment in $(bosh deployments --json | jq -r '.Tables[].Rows[].name')
do
    echo "Working deployment: $deployment"
    bosh -d $deployment ssh --results --column=Instance --column=Stdout -c "sudo /var/vcap/packages/clamav/bin/freshclam -V --config-file=/var/vcap/jobs/clamav/conf/freshclam.conf"
done
