#!/bin/bash

if [ "$#" -ne 2 ]; then
  echo
  echo "Usage:"
  echo "   ./validate-admins.sh <uaa-target> <uaa-admin-client-secret>"
  echo
  echo "   EX:  ./validate-admins.sh login.fr.cloud.gov S3c4Et"
  echo 
  echo "   Obtain uaa-admin-client-secret by running:"
  echo 
  echo "   credhub get -n \"/bosh/cf-{environment-name}/uaa_admin_client_secret\" | grep value | sed -r 's/value: //g'"
  echo
    exit 1
fi

uaac target $1
uaac token client get admin -s $2

echo -e "admins for admin ui\n"
for uuid in $(uaac groups -a members "displayName eq 'admin_ui.admin'" | grep value | awk '{print $2}'); do 
    uaac users -a username "id eq '${uuid}'" | grep username | awk '{print $2}'
done

echo -e "\n\nadmins for cloud_controller (cf)\n"
for uuid in $(uaac groups -a members "displayName eq 'cloud_controller.admin'" | grep value | awk '{print $2}'); do 
    uaac users -a username "id eq '${uuid}'" | grep username | awk '{print $2}'
done

echo -e "\n\nadmins for concourse\n"
for uuid in $(uaac groups -a members "displayName eq 'concourse.admin'" | grep value | awk '{print $2}'); do 
    uaac users -a username "id eq '${uuid}'" | grep username | awk '{print $2}'
done
