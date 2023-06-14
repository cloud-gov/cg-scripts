#!/bin/bash

# import common functions
. "$(dirname "$0")/../lib/common.sh"

function usage {
cat >&2 <<EOM

usage: $(basename "$0") [Service Name]

options:

  $0 -h                         Display this help message.
  $0 -q                         Suppress status output on stderr
  $0 -o org                     Set org [default current target]
  $0 -s space                   Set space [default current target]

query CF platform and AWS to provide detailed
service instance information as json on stdout.
Currently supports RDS, S3, Redis and Elasticsearch.
EOM
}

function query_rds {
  local service_key=$1
  # get the db instance name
  local hostname=$(echo $service_key | jq -r .host)
  local hostsplit=(${hostname//./ })
  local db_instance_name=${hostsplit[0]}

  echo_green "Retrieving AWS RDS instance information" >&3
  # get the rds db_instance info
  output=$(aws rds describe-db-instances --db-instance-identifier ${db_instance_name} | jq -r .DBInstances[0])
  echo ${output}
}

 function query_es {
  local service_key=$1
  # get the db instance name
  local hostname=$(echo $service_key | jq -r .host)
  local hostsplit=(${hostname//./ })
  local hostname=${hostsplit[0]}
  local hostsplit=(${hostname//-/ })
  local es_instance_name="${hostsplit[1]}-${hostsplit[2]}-${hostsplit[3]}-${hostsplit[4]}"

  echo_green "Retrieving AWS ES instance information for ${es_instance_name}" >&3
  # get the rds db_instance info
  output=$(aws opensearch describe-domain --domain-name ${es_instance_name} | jq -r .DomainStatus)
  echo ${output}
}

 function query_redis {
  local service_key=$1
  # get the db instance name
  local hostname=$(echo $service_key | jq -r .host)
  local hostsplit=(${hostname//./ })
  #local redis_repl_name="${hostsplit[1]}"
  local redis_master="${hostsplit[1]}-001"
  echo_green "Retrieving AWS Redis instance information" >&3
  # get the rds db_instance info
  output=$(aws elasticache describe-cache-clusters --cache-cluster-id ${redis_master})
  echo ${output}
}

function query_s3 {
  local service_key=$1
  # get the db instance name
  local bucketname=$( echo $service_key | jq -r .bucket)
  echo_green "Retrieving AWS s3 bucket information" >&3
  local bucket_usage=$(aws cloudwatch get-metric-statistics --namespace AWS/S3 --metric-name BucketSizeBytes \
    --start-time $(date -v -1d +%Y-%m-%d) --end-time $(date +%Y-%m-%d) --period 86400 --statistics Maximum \
    --dimensions Name=BucketName,Value=${bucketname} Name=StorageType,Value=StandardStorage\
     --query 'Datapoints[0].Maximum' )
  bucket_usage=${bucket_usage%.*}
  bucket_usage=$(($bucket_usage/1024))
  local bucket_objects=$(aws cloudwatch get-metric-statistics --namespace AWS/S3 --metric-name NumberOfObjects \
    --start-time $(date -v -1d +%Y-%m-%d) --end-time $(date +%Y-%m-%d) --period 86400 --statistics Maximum \
    --dimensions Name=BucketName,Value=$bucketname Name=StorageType,Value=AllStorageTypes \
    --query 'Datapoints[0].Maximum')
  local output=$(cat<<EOM
{
  "BucketName": "${bucketname}",
  "BucketUsageKB": "${bucket_usage}",
  "BucketObjectCount": "${bucket_objects}"
}
EOM
)
echo ${output}
}

# Get default org cf tarand space from current target
target_output=$(cf target)
quiet="false"
ORG=$(echo "${target_output}" | grep 'org:' | awk '{print $2}')
SPACE=$(echo "${target_output}" | grep 'space:' | awk '{print $2}')

while getopts ":hqo:s:" opt; do
  case ${opt} in
    h )
        usage
        exit 0
        ;;
    q )
        quiet="true"
        ;;
    o )
        ORG=$OPTARG
        ;;
    s )
        SPACE=$OPTARG
        ;;
    \? )
        raise "Invalid Option: $OPTARG"

        ;;
    : )
        raise "Invalid option: $OPTARG requires an argument"
        ;;
  esac
done
shift $((OPTIND -1))
# check for args
[ $# -ne 1 ] && raise_with_usage 'Must provide 1 argument'

if [ $quiet = false ]; then
  exec 3>&2
else
  exec 3>/dev/null
fi

service_name=$1
services_endpoint="/v3/service_instances/?names=${service_name}"
if [ "${ORG}" != "" ]; then
    organization_guid=$(cf curl "/v3/organizations/?names=${ORG}" | jq -r .resources[].guid)
    services_endpoint="${services_endpoint}&organization_guids=${organization_guid}"
    if [ "${SPACE}" != "" ]; then
        space_guid=$(cf curl "/v3/spaces/?names=${SPACE}&organization_guids=${organization_guid}" | jq -r .resources[].guid)
        services_endpoint="${services_endpoint}&space_guids=${space_guid}"
    fi
else
    raise_with_usage "No Org or space provided or set, either set your target or provide org and space"
fi
echo_green "Retrieving service info from broker" >&3
# Get the service info and verify
service_json=$(cf curl ${services_endpoint})
#echo "${service_json}"
service_count=$( echo ${service_json} | jq -r '.resources | length')
#echo $service_count
if [[ ${service_count} -eq 0 ]]; then
    raise "No service named $service_name in $ORG and $SPACE"
fi

service_guid=$( echo ${service_json} | jq -r .resources[0].guid)
service_plan_guid=$( echo ${service_json} | jq -r .resources[0].relationships.service_plan.data.guid)
service_plan_json=$(cf curl "/v3/service_plans/${service_plan_guid}")
service_plan_name=$(echo ${service_plan_json}| jq -r .name)
service_offering_guid=$(echo ${service_plan_json} | jq -r .relationships.service_offering.data.guid)
service_offering_json=$(cf curl "/v3/service_offerings/${service_offering_guid}")
service_offering_name=$(echo ${service_offering_json}| jq -r .name)

echo_green "Creating temporary service key" >&3
# Make a service key to get the AWS info
key_name="${service_name}-key-$(openssl rand -hex 5)"
payload=$(cat<<EOF
{
    "type": "key",
    "name": "${key_name}",
    "relationships": {
      "service_instance": {
        "data": {
          "guid": "${service_guid}"
        }
      }
    }
}
EOF
)

# create service key
create_key=$(cf curl -d "${payload}" "/v3/service_credential_bindings")
service_key_guid=$(cf curl /v3/service_credential_bindings?names=${key_name} | jq -r .resources[0].guid)

# get key details
echo_green "Getting temporary service key details" >&3
# the broker may take a second or two to finsh the async credential creation so poll
service_key_details="null"
while [ "${service_key_details}" == "null" ]; do
  service_key_details=$(cf curl /v3/service_credential_bindings/${service_key_guid}/details | jq -r .credentials)
  # echo_red "${service_key_details}" >&2
  sleep 1
done
# Delete key
echo_green "Deleting temporary service key" >&3
delete_key=$(cf curl -X DELETE "/v3/service_credential_bindings/${service_key_guid}")

# find the service info based off offering name
echo_green "Retrieving AWS Service instance information for type: ${service_offering_name}" >&3
if [ "${service_offering_name}" == "aws-rds" ]; then
    aws_instance_info=$(query_rds "${service_key_details}" )
elif [ "${service_offering_name}" == "aws-elasticsearch" ]; then
    aws_instance_info=$(query_es "${service_key_details}" )
elif [ "${service_offering_name}" == "aws-elasticache-redis" ]; then
   aws_instance_info=$(query_redis "${service_key_details}" )
elif [ "${service_offering_name}" == "s3" ]; then
    aws_instance_info=$(query_s3 "${service_key_details}" )
else
  echo_red "Service Type: ${service_offering_name} is not yet supported" >&2
fi

cf_output=$(cat<<EOM
{
  "ServiceName": "${service_name}",
  "ServiceGuid": "${service_guid}",
  "ServicePlan": "${service_plan_name}",
  "ServiceOffering": "${service_offering_name}"
}
EOM
)

# merge and output well formatted json via jq slurp
(echo ${cf_output}; echo ${aws_instance_info} ) | jq -s '.[0]+.[1]'
