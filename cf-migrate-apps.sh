#!/bin/bash

set -e

if [ "$#" -lt 1 ]; then
  printf "Usage:\n\n\t\$./cf-migrate-apps.sh <app_org/app_space>\n\n"
  exit 1
fi
APP_PATH=$1
for app in $(cf audit-stack | grep $APP_PATH | grep cflinuxfs2 | awk '{print $1}' | awk -F/ '{print $3}'); do cf change-stack $app cflinuxfs3; done
