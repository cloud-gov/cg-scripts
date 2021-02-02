#!/bin/bash

# Retrieves all users who are not part of an orgs with an agreement (sandbox users) and outputs to a CSV file.

# Requires cf CLI version 7+ and jq to work.

# NOTE:  The script logic is based on the assumption that all sandbox orgs do not have agreements.  

# NOTE:  Only works if there are 5,000 or less orgs in the system at this time.


set -e

# Printing headers for csv file 
printf 'User_Name,Agency,Account_creation_date,Org_Name\n' > users_to_contact.csv

# Getting all non "sandbox-" org guids and storing it to a text file for later use 
ORG_IDS=$(cf curl '/v3/organizations?per_page=5000'| jq -r '.resources |= sort_by(.name) | .resources[] | select(.name | contains("sandbox") | not ) | .guid')

for ORG_ID in $ORG_IDS; do

    cf curl "/v3/roles?organization_guids=$ORG_ID" | jq -r '.resources[] | .relationships.user.data.guid' >> non_sandbox_org_users.txt

done

# Getting all "sandbox-" org guids
SANDBOX_ORG_IDS=$(cf curl '/v3/organizations?per_page=5000'| jq -r '.resources |= sort_by(.name) | .resources[] | select(.name | contains("sandbox")) | .guid')

for SAORG_ID in $SANDBOX_ORG_IDS; do

    # Getting users for evey sandbox org
    ORG_USERS=$(cf curl "/v3/roles?organization_guids=$SAORG_ID" | jq -r '.resources[] | .relationships.user.data.guid')

    for ORG_USER in $ORG_USERS; do 

        
        # Checking to see if user is also part of a non sandbox account. 
        if grep -q "$ORG_USER" non_sandbox_org_users.txt
        then

            echo "user is also part of non sandbox org skipping"

        else

            # Getting user name, agency, and date account was created
            ORG_USER_NAME=$(cf curl "/v3/users/$ORG_USER" | jq -r ' select(.username != null) | [ .presentation_name, .origin, .created_at ] | @csv' | sed 's/"//g')

            if [[ "$ORG_USER_NAME" != "" ]]; then

                # Getting org name for user
                ORG_NAME=$(cf curl "/v3/organizations/$SAORG_ID" | jq -r '.name')               
                
                # Print user who is not part of a sandbox account to csv 
                printf '%s, %s\n' "${ORG_USER_NAME}" "${ORG_NAME}" >> users_to_contact.csv
                echo "users_to_contact csv printed successfully"
            fi 
        fi
    done
done

# Removing file with non sandbox orgs user guids 
echo "script executed sucessfully, removing temp file "
rm -f non_sandbox_org_users.txt 
