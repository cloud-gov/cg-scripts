#!/bin/bash

# Checks for kernel modules in bosh instances

if [[ -z ${MODULE} || ${1} =~ -h ]]; then
    echo "usage: MODULES=module [DEPLOYMENT=deployment] check-for-module-loaded.sh"
    exit 2
fi

if [[ -n ${DEPLOYMENT} ]]; then
    echo "Deployment set - only checking ${DEPLOYMENT}"
    ${DEPLOYMENTS}=${DEPLOYMENT}
else
    echo "Getting all deployments"
    DEPLOYMENTS=$(bosh deployments --json| jq -r '.Tables[].Rows[].name')
fi

present=""
not_present=""
error=""
for DEPLOYMENT in ${DEPLOYMENTS}; do
    echo "Getting modules for ${DEPLOYMENT}"
    results=$(bosh ssh -d ${DEPLOYMENT} -r --json -c "grep ${MODULE} /proc/modules")
    for instance in $(echo ${results} | jq -r '.Tables[].Rows[] | select(.exit_code == "1").instance'); do
        not_present+="${DEPLOYMENT}/${instance} "
    done
    for instance in $(echo ${results} | jq -r '.Tables[].Rows[] | select(.exit_code == "0").instance'); do
        present+="${DEPLOYMENT}/${instance} "
    done
    for instance in $(echo ${results} | jq -r '.Tables[].Rows[] | select(.exit_code != "0" and .exit_code != "1").instance'); do
        error+="$DEPLOYMENT/${instance} "
    done
done

echo "==========================================="
echo "::     Instances without this module     ::"
echo "==========================================="
for instance in ${not_present}; do
    echo ${instance}
done
echo "==========================================="
echo "::      Instances with this module       ::"
echo "==========================================="
for instance in ${present}; do
    echo ${present}
done
if [[ -n $error ]]; then
    echo "==========================================="
    echo "::          Errored Instances            ::"
    echo "==========================================="
    echo ${error}
fi
