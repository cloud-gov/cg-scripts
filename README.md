# cloud-foundry-scripts
Scripts to assist with the configuration and operation of Cloud Foundry.

## Make admins

These steps correspond to the [steps for creating admins](http://docs.cloudfoundry.org/adminguide/uaa-user-management.html#creating-admin-users). Substitute `cloud.gov` for the appropriate environment.

1. Have the user log in via https://login.cloud.gov.
1. Run

    ```bash
    ./make-admin.sh uaa.cloud.gov <user>
    ```
