#!/bin/bash 

# set -e -u -o pipefail

main(){
    echo -n "Date: "; date
    uaac target $1  2> >(grep -v SameSite)
    uaac token client get admin -s $2 2> >(grep -v SameSite)

    echo -e "admins for admin ui\n"
    for uuid in $(uaac groups -a members "displayName eq 'admin_ui.admin'" 2> >(grep -v SameSite) | grep value | awk '{print $2}'); do 
        uaac users -a username "id eq '${uuid}'"  2> >(grep -v SameSite)| grep username | awk '{print $2}'
    done

    echo -e "\n\nadmins for cloud_controller (cf)\n"
    for uuid in $(uaac groups -a members "displayName eq 'cloud_controller.admin'"  2> >(grep -v SameSite)| grep value | awk '{print $2}'); do 2> >(grep -v SameSite)
        uaac users -a username "id eq '${uuid}'"  2> >(grep -v SameSite)| grep username | awk '{print $2}'
    done

    echo -e "\n\nadmins for global_auditor (cf)\n"
    for uuid in $(uaac groups -a members "displayName eq 'cloud_controller.global_auditor'"  2> >(grep -v SameSite) | grep value | awk '{print $2}'); do 
        uaac users -a username "id eq '${uuid}'"  2> >(grep -v SameSite)| grep username | awk '{print $2}'
    done

    echo -e "\n\nadmins for concourse\n"
    for uuid in $(uaac groups -a members "displayName eq 'concourse.admin'"  2> >(grep -v SameSite) | grep value | awk '{print $2}'); do 
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
  easta|eastb)
    short_boshname=$(echo $BOSH_DIRECTOR_NAME | cut -c1,5)
    secret=$(credhub get -n /bosh/cf-${BOSH_DIRECTOR_NAME}/uaa_admin_client_secret | grep value | sed -r 's/value: //g')
    main login.$short_boshname.fr.cloud.gov $secret
    ;;
  "West Bro")
    secret=$(credhub get -n /bosh/cf-westb/uaa_admin_client_secret | grep value | sed -r 's/value: //g')
    main login.wb.fr.cloud.gov $secret
    ;;
  "West Coin")
    secret=$(credhub get -n /bosh/cf-westc/uaa_admin_client_secret | grep value | sed -r 's/value: //g')
    main login.wc.fr.cloud.gov $secret
    ;;


  *)
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
    else
        main $1 $2
    fi
    ;;
esac
