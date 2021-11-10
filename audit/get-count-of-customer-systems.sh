#!/bin/bash

# Counts the number of current customer systems in the platform.

# Customer systems are defined as an organization per our public documentation:

# "First, a quick definition: a customer “system” is typically an org that
# contains spaces (such as staging and production spaces), applications, and
# service instances that serve together as sub-components of the system. The
# exact definition and boundary of “system” is up to your agency."

# https://cloud.gov/docs/compliance/ato-process/#how-customer-system-atos-work

# This means we need to exclude the following orgs:
# - sandbox-* (all sandbox orgs)
# - cf-* (platform-specific orgs)
# - cloud-gov-* (cloud.gov-specific orgs)

# All remaining organizations are paid for by customers, be they prototypes,
# FISMA low, or # FISMA moderate.

echo "Getting total count of customer systems..."
echo

# Retrieve the total number of customer organizations.
total_orgs=$(cf orgs)
total_customer_orgs=$(echo "$total_orgs" | \grep -vE '^(sandbox|cf|cloud\-gov)' | \wc -l | xargs)
total_customer_orgs_no_prototypes=$(echo "$total_orgs" | \grep -vE '^(sandbox|cf|cloud\-gov)|prototyping$' | \wc -l | xargs)

# Print the final results.
echo "Total number of customer organizations: $total_customer_orgs"
echo "Total number of customer organizations excluding prototyping orgs: $total_customer_orgs_no_prototypes"
