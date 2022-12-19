#!/bin/bash

# set -e -u -o pipefail

main(){
    echo -n "Date: "; date
    uaac target $1  2> >(grep -v SameSite)
    uaac token client get admin -s $2 2> >(grep -v SameSite)

    echo -e "Support users for pages.support group\n"
    for uuid in $(uaac groups -a members "displayName eq 'pages.support'" 2> >(grep -v SameSite) | grep value | awk '{print $2}'); do
        uaac users -a username "id eq '${uuid}'"  2> >(grep -v SameSite)| grep username | awk '{print $2}'
    done

    echo -e "\n\nAdmin users for pages.admins group\n"
    for uuid in $(uaac groups -a members "displayName eq 'pages.admin'"  2> >(grep -v SameSite)| grep value | awk '{print $2}'); do 2> >(grep -v SameSite)
        uaac users -a username "id eq '${uuid}'"  2> >(grep -v SameSite)| grep username | awk '{print $2}'
    done

    echo -e "\n\nUsers for concourse Pages team\n"
    for uuid in $(uaac groups -a members "displayName eq 'concourse.pages'"  2> >(grep -v SameSite) | grep value | awk '{print $2}'); do
        uaac users -a username "id eq '${uuid}'"  2> >(grep -v SameSite)| grep username | awk '{print $2}'
    done
}

case "$BOSH_DIRECTOR_NAME" in
  PRODUCTION)
    secret=$(credhub get -n /bosh/cf-production/uaa_admin_client_secret | grep value | sed -r 's/value: //g')
    main login.fr.cloud.gov $secret
    ;;
  Tooling)
    secret=$(credhub get -n /toolingbosh/opsuaa/uaa_admin_client_secret | grep value | sed -r 's/value: //g')
    main opsuaa.fr.cloud.gov $secret
    ;;
  staging)
    secret=$(credhub get -n /bosh/cf-staging/uaa_admin_client_secret | grep value | sed -r 's/value: //g')
    main login.fr-stage.cloud.gov $secret
    ;;


  *)
    if [ "$#" -ne 2 ]; then
        echo
        echo "Usage:"
        echo "   ./validate-pages-admins.sh <uaa-target> <uaa-admin-client-secret>"
        echo
        echo "   EX:  ./validate-pages-admins.sh login.fr.cloud.gov S3c4Et"
        echo
        echo "   Obtain uaa-admin-client-secret by running:"
        echo
        echo "   credhub get -n \"/bosh/cf-{environment-name}/uaa_admin_client_secret\" | grep value | sed -r 's/value: //g'"
        echo
        exit 1
    else
        main $1 $2
    fi
    ;;
esac
