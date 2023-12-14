#!/bin/bash

function query_org_name {
  if [ -n "$ORG_GUID" ]; then
    ORG_NAME=$(cf curl "/v3/organizations/$ORG_GUID" | jq -r '.name')
    echo "$ORG_NAME"
  fi
}

function query_space_name {
  if [ -n "$SPACE_GUID" ]; then
    SPACE_NAME=$(cf curl "/v3/spaces/$SPACE_GUID" | jq -r '.name')
    echo "$SPACE_NAME"
  fi
}

function query_service_instance_name {
  if [ -n "$INSTANCE_GUID" ]; then
    SERVICE_NAME=$(cf curl "/v3/service_instances/$INSTANCE_GUID"  | jq -r '.name')
    echo "$SERVICE_NAME"
  fi
}
