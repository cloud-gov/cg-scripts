#!/bin/bash

if [ "$#" -ne 1 ]; then
  echo
  echo "Usage:"
  echo "   ./delete-org.sh <org name>"
  echo

  exit 1
fi

read -p "This script will delete all the resources an org and all of it resources (services, apps, routes, spaces). Are you sure? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
  exit 1
fi

ORG=$1
ORG_GUID=$(cf org "$ORG" --guid | tr -d '\n')

for space_info in $(cf curl "/v3/spaces?organization_guids=$ORG_GUID" | jq -r '.resources[] | (.name)+","+(.guid)'); do
  IFS=',' read -r -a array <<< "$space_info"
  SPACE_NAME="${array[0]}"
  SPACE_GUID="${array[1]}"

  printf "\ndeleting services for org %s in space %s\n\n" "$ORG" "$SPACE_NAME"
  for service_info in $(cf curl "/v3/service_instances?space_guids=$SPACE_GUID" | jq -r '.resources[] | (.name)+","+(.guid)'); do
    IFS=',' read -r -a array <<< "$service_info"
    SERVICE_NAME="${array[0]}"
    SERVICE_GUID="${array[1]}"

    for service_key_name in $(cf curl "/v3/service_credential_bindings?type=key&service_instance_guids=$SERVICE_GUID" | jq -r '.resources[].name'); do
      echo "deleting service key $service_key_name for $SERVICE_NAME"
      cf delete-service-key "$SERVICE_NAME" "$service_key_name" -f
    done

    cf delete-service "$SERVICE_NAME" -f
  done

  printf "\ndeleting apps for org %s in space %s\n\n" "$ORG" "$SPACE_NAME"
  for app in $(cf curl "/v3/apps?space_guids=$SPACE_GUID" | jq -r '.resources[].name'); do
    cf delete "$app" -f -r # also delete routes for app
  done

  printf "\ndeleting routes for org %s in space %s\n\n" "$ORG" "$SPACE_NAME"
  for route_url in $(cf curl "/v3/routes?space_guids=$SPACE_GUID" | jq -r '.resources[].url'); do
    cf delete-route "$route_url" -f
  done
done