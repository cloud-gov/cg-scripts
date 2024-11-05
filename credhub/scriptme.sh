#!/bin/bash
set -e -u
export CREDHUB_CA_CERT="$(pwd)/${CREDHUB_CA_CERT}"

cat << EOF > slots.value
export SLOT1="$(credhub get -n /concourse/pages/com-waf-search-string-pages-slot-1 -q)"
export SLOT2="$(credhub get -n /concourse/pages/com-waf-search-string-pages-slot-2 -q)"
EOF

exit 1
