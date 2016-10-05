# cloud-foundry-scripts
Scripts to assist with the configuration and operation of Cloud Foundry.

## Managing Admins
### Creating admins

These steps correspond to the [steps for creating admins](http://docs.cloudfoundry.org/adminguide/uaa-user-management.html#creating-admin-users).

1. Have the user log in via https://login.cloud.gov.
1. ```uaac target <CF_UAA_FQDN>```
1. ```uaac token client get admin -s <CF_UAA_ADMINCLIENT_PASSPHRASE>```
1. Run

    ```bash
    ./make-cf-admin.sh <EMAIL_ADDRESS>
    ```
1. ```uaac target <OPS_UAA_FQDN>```
1. ```uaac token client get admin -s <OPS_UAA_ADMINCLIENT_PASSPHRASE>```
1. Run

    ```bash
    ./make-ops-admin.sh <EMAIL_ADDRESS>
    ```

### Removing admins
1. ```uaac target <CF_UAA_FQDN>```
1. ```uaac token client get admin -s <CF_UAA_ADMINCLIENT_PASSPHRASE>```
1. Run

    ```bash
    ./make-cf-admin.sh -r <EMAIL_ADDRESS>
    ```
1. ```uaac target <OPS_UAA_FQDN>```
1. ```uaac token client get admin -s <OPS_UAA_ADMINCLIENT_PASSPHRASE>```
1. Run

    ```bash
    ./make-ops-admin.sh -r <EMAIL_ADDRESS>
    ```

## Creating deployer users
1. Ensure the user running this is a CF admin (see [Creating admins](#creating-admins))
1. Run

    ```bash
    ./cf-create-deployer-user.sh <ORG>
