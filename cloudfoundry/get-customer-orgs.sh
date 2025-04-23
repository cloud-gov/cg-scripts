#!/bin/bash

CUSTOMER_ORG_FILTER=$(echo "org-type=customer" | jq -Rr @uri)

# NOTE: does not handle paging
cf curl "/v3/organizations?per_page=5000&label_selector=$CUSTOMER_ORG_FILTER"
