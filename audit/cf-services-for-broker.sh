#!/bin/bash

##
# A script to capture service inventory based on the service broker
# Adapted from https://github.com/cloudfoundry-community/cloudfoundry-utils/blob/master/bin/cf-services-for-broker
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
	echo cf-services-for-broker ${VERSION}
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
		cf curl "${url}" > ${path}
	fi
	echo ${path}
}

function process_serviceinstance() {
	set -e
	service_instance_guid=$1
	service_name=$(cat $(cf_curl /v2/service_instances/${service_instance_guid}) | jq -r '.entity.name')
  service_plan_url=$(cat $(cf_curl /v2/service_instances/${service_instance_guid}) | jq -r '.entity.service_plan_url')
  service_plan_name=$(cat $(cf_curl ${service_plan_url}) | jq -r '.entity.name')
	n=0
	next_bindings_url="/v2/service_bindings?q=service_instance_guid:${service_instance_guid}"
	apps=""
	count=$(cat $(cf_curl ${next_bindings_url}) | jq -r '.total_results')

	debug "    found service ${service_name} with guid {${service_instance_guid}}"
	space_guid=$(cat $(cf_curl /v2/service_instances/${service_instance_guid}) | jq -r '.entity.space_guid')
	space_name=$(cat $(cf_curl /v2/spaces/${space_guid}) | jq -r '.entity.name')
	debug "    -- in ${org_name} / ${space_name}"
	org_guid=$(cat $(cf_curl /v2/spaces/${space_guid}) | jq -r '.entity.organization_guid')
	org_name=$(cat $(cf_curl /v2/organizations/${org_guid}) | jq -r '.entity.name')

	if [[ ${count} > 0 ]]; then
		next_bindings_url="/v2/service_bindings?q=service_instance_guid:${service_instance_guid}"
		while [[ ${next_bindings_url} != "null" ]]; do
			for app_guid in $(cat $(cf_curl ${next_bindings_url}) | jq -r '.resources[].entity.app_guid'); do
				app_name=$(cat $(cf_curl /v2/apps/${app_guid}) | jq -r '.entity.name')
				debug "      found app '${app_name}' with guid {${app_guid}}"


				app_name=${app_name:-(${app_guid})}
				if [[ $n == 0 ]]; then
					echo -ne "${service_name}\t${count}\t"
				else
					echo -ne " \t \t"
				fi
				echo -e "${app_name}\t${service_plan_name}\t${org_name}\t${space_name}"
				n=$(( n + 1 ))
			done

			next_bindings_url=$(cat $(cf_curl ${next_bindings_url}) | jq -r -c ".next_url")
		done
	else
		echo -e "${service_name}\t${n}\t \t${service_plan_name}\t${org_name}\t${space_name}"
	fi
}

function traverse_serviceinstances_for_plan() {
	set -e
	service_plan_guid=$1
	next_serviceinstance_url="/v2/service_instances?q=service_plan_guid:${service_plan_guid}"
	while [[ ${next_serviceinstance_url} != "null" ]]; do
		for service_instance_guid in $(cat $(cf_curl ${next_serviceinstance_url}) | jq -r '.resources[].metadata.guid'); do
			debug "    found service instance '${service_name}' with guid {${service_instance_guid}}"
			process_serviceinstance ${service_instance_guid}
		done
		next_serviceinstance_url=$(cat $(cf_curl ${next_serviceinstance_url}) | jq -r -c ".next_url")
	done
}

function traverse_serviceplans_for_broker() {
	set -e
	broker_guid=$1
	next_serviceplan_url="/v2/service_plans?q=service_broker_guid:${broker_guid}"
	while [[ ${next_serviceplan_url} != "null" ]]; do
		for service_plan_guid in $(cat $(cf_curl ${next_serviceplan_url}) | jq -r '.resources[].metadata.guid'); do
			debug "  found service plan guid {${service_plan_guid}} for service"
			traverse_serviceinstances_for_plan ${service_plan_guid}
		done
		next_serviceplan_url=$(cat $(cf_curl ${next_serviceplan_url}) | jq -r -c '.next_url')
	done
}

function services_for_broker() {
	set -e
	broker=$1
	broker_count=$(cat $(cf_curl /v2/service_brokers?q=name:${broker}) | jq -r '.total_results')
	if [[ ${broker_count} == 0 ]]; then
		echo "Could not find broker '${broker}'" >&2
		exit 1
	else
		if [[ ${broker_count} != 1 ]]; then
			echo "Too many brokers found matching '${broker}'! Try narrowing your search" >&2
			exit 1
		fi
	fi
	broker_guid=$(cat $(cf_curl /v2/service_brokers?q=name:${broker}) | jq -r '.resources[].metadata.guid')
	debug "broker '${broker}' has guid {${broker_guid}}"

	echo -e "Service\t#\tBound Application(s)\tPlan\tOrganization\tSpace"
	echo -e "-------\t-\t--------------------\t----\t------------\t-----"
	traverse_serviceplans_for_broker ${broker_guid}
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
services_for_broker ${BROKER_NAME} | column -t -s "	"
