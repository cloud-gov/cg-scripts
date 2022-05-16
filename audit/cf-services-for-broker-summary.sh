#!/bin/bash

##
# A script to capture summary of servivce inventory based on the service broker
#
# Added `Plan` field to script to capture the service plan used.
#
# The script returns a table like the following example for the aws-broker
#
# Service                      #  Bound Application(s)            Plan              Organization         Space
# -------                      -  --------------------            ------------      ------------         -----
# org-db-shared                0                                  shared-psql       org-a                development
# org-db-psql                  0                                  shared-psql       org-b                staging
# production-db                2  app-a                           medium-psql       org-a                production
#                                 app-b                           medium-psql       org-a                production
# dev-mysql                    1  dev-app                         shared-mysql      org-b                development
# prod-mysql                   1  prod-app                        medium-mysql      org-b                production
# dev-redis                    0                                  BETA-redis-dev    org-a                development
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
		debug "No cached data found - cf curl ${url}"
		cf curl "${url}" > "${path}"
	fi
	
    debug "Cached data found - cf curl ${url}, path ${path}"
    cat "${path}"
}

function process_serviceinstance() {
	set -e

	service_instance_guid=$1
	service_name=$(cf_curl "/v3/service_instances/${service_instance_guid}" | jq -r '.name')
    service_plan_url=$(cf_curl "/v3/service_instances/${service_instance_guid}" | jq -r '.relationships.service_plan.data.guid')
    service_plan_name=$(cf_curl "/v3/service_plans/${service_plan_url}" | jq -r '.name')

	# n=0
	next_bindings_url="/v3/service_credential_bindings?service_instance_guids=${service_instance_guid}"
	count=$(cf_curl "${next_bindings_url}" | jq -r '.pagination.total_results | tonumber')

	# debug "    found service ${service_name} with guid {${service_instance_guid}}"
	# space_guid=$(cat $(cf_curl /v3/service_instances/${service_instance_guid}) | jq -r '.relationships.space.data.guid')
	# space_name=$(cat $(cf_curl /v3/spaces/${space_guid}) | jq -r '.name')
	# debug "    -- in ${org_name} / ${space_name}"
	# org_guid=$(cat $(cf_curl /v3/spaces/${space_guid}) | jq -r '.relationships.organization.data.guid')
	# org_name=$(cat $(cf_curl /v3/organizations/${org_guid}) | jq -r '.name')

    echo -e "${service_plan_name}\t${count}\t "

	# if [[ ${count} -gt 0 ]]; then
	# 	next_bindings_url="/v3/service_credential_bindings?service_instance_guids=${service_instance_guid}"
	# 	while [[ ${next_bindings_url} != "null" ]]; do
	# 		for app_guid in $(cat $(cf_curl ${next_bindings_url}) | jq -r '.resources[].relationships.app.data.guid'); do
	# 			app_name=$(cat $(cf_curl /v3/apps/${app_guid}) | jq -r '.name')
	# 			debug "      found app '${app_name}' with guid {${app_guid}}"


	# 			app_name=${app_name:-(${app_guid})}
	# 			if [[ $n == 0 ]]; then
	# 				echo -ne "${service_name}\t${count}\t"
	# 			else
	# 				echo -ne " \t \t"
	# 			fi
	# 			echo -e "${app_name}\t${service_plan_name}\t${org_name}\t${space_name}"
	# 			n=$(( n + 1 ))
	# 		done

	# 		next_bindings_url=$(cat $(cf_curl ${next_bindings_url}) | jq -r -c ".pagination.next.href")
	# 	done
	# else
	# 	echo -e "${service_name}\t${n}\t \t${service_plan_name}\t${org_name}\t${space_name}"
	# fi
}

function traverse_serviceinstances_for_plan() {
	set -e
	service_plan_guid=$1
	next_serviceinstance_url="/v3/service_instances?service_plan_guids=${service_plan_guid}"
	while [[ ${next_serviceinstance_url} != "null" ]]; do
		for service_instance_guid in $(cf_curl "${next_serviceinstance_url}" | jq -r '.resources[].guid'); do
			debug "    found service instance '${service_name}' with guid {${service_instance_guid}}"
			process_serviceinstance "${service_instance_guid}"
		done
		next_serviceinstance_url=$(cf_curl "${next_serviceinstance_url}" | jq -r -c ".pagination.next.href")
	done
}

function traverse_serviceplans_for_broker() {
	set -e
	broker_guid=$1
	next_serviceplan_url="/v3/service_plans?service_broker_guids=${broker_guid}"
	while [[ ${next_serviceplan_url} != "null" ]]; do
		for service_plan_guid in $(cf_curl "${next_serviceplan_url}" | jq -r '.resources[].guid'); do
			debug "  found service plan guid {${service_plan_guid}} for service"
			traverse_serviceinstances_for_plan "${service_plan_guid}"
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

echo -e "...gathering data from Cloud Foundry (this may take a while )..." >&2
services_for_broker "${BROKER_NAME}" | column -t -s "	"
