#!/bin/bash

CERT_NAME=""

# find cert 
#   stop if not found
# validate date expiring
#   stop if not expiring
# find ca cert_signedby 
# find expiry date for ca
#   if ca not expiring -- regen cert
#   else renew ca
function regen_cert () {}
function cert_info () {}
function cert_expiration () {}
function get_signing_ca () {}
function get_signed_certs () {}
function renew_ca() {}

cert_info=$(credhub get -n ${CERT_NAME} -j)
cert_dates=$(credhub get -n ${CERT_NAME} -j | jq -r '.value.certificate' | openssl x509 -noout -dates)
ca_dates=$(credhub get -n ${CERT_NAME} -j | jq -r '.value.ca' | openssl x509 -noout -dates)
CERT_SIGNEDBY=$(credhub curl -p "/api/v1/certificates?name=${CERT_NAME}" | jq -r ".certificates[].signed_by")
signing_ca_id=$(credhub curl -p "/api/v1/certificates?name=${CERT_SIGNEDBY}" | jq -r '.certificates[].id')