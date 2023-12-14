#!/bin/bash

function query_org {
  if [ -n "$ORG_GUID" ]; then
    ORG_NAME=$(cf curl "/v3/organizations/$ORG_GUID" | jq -r '.name')
    echo "$ORG_NAME"
  fi
}

function query_space {
  if [ -n "$SPACE_GUID" ]; then
    SPACE_NAME=$(cf curl "/v3/spaces/$SPACE_GUID" | jq -r '.name')
    echo "$SPACE_NAME"
  fi
}
