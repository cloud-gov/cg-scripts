#!/bin/bash

set -e
set -x

if [ "$#" -ne 2 ]; then
  echo "Usage:\n\n\t./make-admin.sh <uaa> <user>"
  exit 1
fi
TARGET=$1
USER=$2

if ! hash uaac 2>/dev/null; then
  gem install cf-uaac
fi

uaac target $TARGET

# fail quietly if they already have these permissions
uaac member add cloud_controller.admin $USER || true
uaac member add uaa.admin $USER || true
uaac member add scim.read $USER || true
uaac member add scim.write $USER || true
uaac member add admin_ui.admin $USER || true

echo "DONE"
