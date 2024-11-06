#!/bin/bash
set -e -u
#export CREDHUB_CA_CERT="$(pwd)/${CREDHUB_CA_CERT}"

# Load up current values
echo "Looking up Pages values..."
PAGES_SLOT_1="$(credhub get -n /concourse/pages/com-waf-search-string-pages-slot-1 -q)"
PAGES_SLOT_2="$(credhub get -n /concourse/pages/com-waf-search-string-pages-slot-2 -q)"

echo "Looking up Main values..."
MAIN_SLOT_1="$(credhub get -n /concourse/main/aws-admin/com-waf-search-string-pages-slot-1 -q)"
MAIN_SLOT_2="$(credhub get -n /concourse/main/aws-admin/com-waf-search-string-pages-slot-2 -q)"
               
# Compare variables
echo  "Performing compares..."
if [[ "$PAGES_SLOT_1" != "$MAIN_SLOT_1" ]]; then
    echo "SLOT 1 is different. Updating main with the value of pages."
    credhub set -n /concourse/main/aws-admin/com-waf-search-string-pages-slot-1 -t value -v "${PAGES_SLOT_1}"
else
    echo "SLOT 1 matches. No changes needed."
fi

# Compare variables
if [[ "$PAGES_SLOT_2" != "$MAIN_SLOT_2" ]]; then
    echo "SLOT 2 is different. Updating main with the value of pages."
    credhub set -n /concourse/main/aws-admin/aws-admin/com-waf-search-string-pages-slot-2 -t value -v "${PAGES_SLOT_2}"
else
    echo "SLOT 2 matches. No changes needed."
fi

echo "~fin~"