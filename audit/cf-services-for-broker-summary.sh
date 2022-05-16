#!/bin/bash

##
# A script to capture summary of servivce inventory based on the service broker
#
# Added `Plan` field to script to capture the service plan used.
#
# The script returns a table like the following example for the aws-broker
#
# Service Plan  # of Instances  # of Bound Application(s)
# ------------  --------------  -------------------------
# shared-psql   1               1
# medium-psql   2               5
# large-psql    3               3
##

set -e

VERSION="(development build)"

if [[ $1 == "-?" || $1 == "-h" || $1 == "--help" ]]; then
	echo "Usage: cf-services-for-broker broker-name"
	echo
	echo  cf-services-for-broker will find all service instances
	echo  that have been created by a specific broker, and print out
	echo  the service instance name, org and space in which it lies,
	echo and what apps are bound to each service instance.
	exit 0
fi

if [[ $1 == "-v" || $1 == "--version" ]]; then
	echo cf-services-for-broker "${VERSION}"
	exit 0
fi

debug() {
	if [[ -n ${DEBUG} && ${DEBUG} != '0' ]];
		then echo >&2 '>> ' "$*"
	fi
}

function cf_curl() {
	set -e
	url=$1
	md5name=$(echo "${url}" | md5 | cut -f1 -d " ")
    path="${tmpdir}/${md5name}"
	if [[ ! -f $path ]]; then
		# debug "No cached data found - cf curl ${url}"
		cf curl "${url}" > "${path}"
	fi
	
    # debug "Cached data found - cf curl ${url}, path ${path}"
    cat "${path}"
}

function get_service_plan_name() {
    service_plan_guid=$1

    service_plan_name=$(cf_curl "/v3/service_plans/${service_plan_guid}" | jq -r '.name')

    debug "  found service plan ${service_plan_name} with guid {${service_plan_guid}}"
    echo "$service_plan_name"
}

function get_service_instance_apps_count() {
	set -e

	service_instance_guid=$1

    service_instance_name=$(cf_curl "/v3/service_instances/${service_instance_guid}" | jq -r '.name')
    debug "    found service instance '${service_instance_name}' with guid {${service_instance_guid}}"

	bindings_url="/v3/service_credential_bindings?service_instance_guids=${service_instance_guid}"
	total_apps_count=$(cf_curl "${bindings_url}" | jq -r '.pagination.total_results | tonumber')
    debug "      found $total_apps_count bound applications for ${service_instance_name}"

    echo $total_apps_count
}

function get_service_plan_summary() {
	set -e
	
    service_plan_guid=$1
    service_plan_name=$(get_service_plan_name "$service_plan_guid")

    next_serviceinstance_url="/v3/service_instances?service_plan_guids=${service_plan_guid}"
    service_plan_instances_count=$(cf_curl "${next_serviceinstance_url}" | jq -r '.pagination.total_results | tonumber')

    total_apps_count=0

    if [[ $service_plan_instances_count -gt 0 ]]; then
        debug "  $service_plan_guid has instances"
        while [[ ${next_serviceinstance_url} != "null" ]]; do
            for service_instance_guid in $(cf_curl "${next_serviceinstance_url}" | jq -r '.resources[].guid'); do
                service_instance_app_count=$(get_service_instance_apps_count "${service_instance_guid}")
                total_apps_count=$((total_apps_count + service_instance_app_count))
            done
            next_serviceinstance_url=$(cf_curl "${next_serviceinstance_url}" | jq -r -c ".pagination.next.href")
        done
        echo -e "${service_plan_name}\t${service_plan_instances_count}\t$total_apps_count"
    fi
}

function traverse_serviceplans_for_broker() {
	set -e
	broker_guid=$1
	next_serviceplan_url="/v3/service_plans?service_broker_guids=${broker_guid}"
	while [[ ${next_serviceplan_url} != "null" ]]; do
		for service_plan_guid in $(cf_curl "${next_serviceplan_url}" | jq -r '.resources[].guid'); do
			debug "  found service plan guid {${service_plan_guid}} for service"
			get_service_plan_summary "${service_plan_guid}"
		done
		next_serviceplan_url=$(cf_curl "${next_serviceplan_url}" | jq -r -c '.pagination.next.href')
	done
}

function services_for_broker() {
	set -e

	broker=$1
	broker_count=$(cf_curl "/v3/service_brokers?names=${broker}" | jq -r '.pagination.total_results')

	if [[ ${broker_count} == 0 ]]; then
		echo "Could not find broker '${broker}'" >&2
		exit 1
	else
		if [[ ${broker_count} != 1 ]]; then
			echo "Too many brokers found matching '${broker}'! Try narrowing your search" >&2
			exit 1
		fi
	fi
	broker_guid=$(cf_curl "/v3/service_brokers?names=${broker}" | jq -r '.resources[].guid')
	debug "broker '${broker}' has guid {${broker_guid}}"

	echo -e "Service Plan\t# of Instances\t# of Bound Application(s)"
	echo -e "------------\t--------------\t-------------------------"
	traverse_serviceplans_for_broker "${broker_guid}"
}

BROKER_NAME=$1
if [[ -z ${BROKER_NAME} ]]; then
	echo "You need to provide a service broker name to find service instances for"
	exit 1
fi

tmpdir=$(mktemp -d)
trap 'rm -rf ${tmpdir:?nothing to remove}' INT TERM QUIT EXIT
debug "set up workspace directory ${tmpdir}"

echo -e "...gathering data from Cloud Foundry (this may take a while)..." >&2
services_for_broker "${BROKER_NAME}" | column -t -s "	"
