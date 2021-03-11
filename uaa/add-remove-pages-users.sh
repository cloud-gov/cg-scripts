#!/bin/bash

## 
# A script to add and remove pages users. 
# Script assumes the user already exist in uaa 
# User must use cg-scripts/uaa/login.sh to login prior to executing this script
##


set -e

# Usage function
function usage {
    echo
    echo "Usage:"
    echo "  $0 [-opetins] <username>"
    echo
    echo "  Options:"
    echo "      -a     :     add user to pages.admin and pages.user groups"
    echo "      -r     :     remove user from pages.admin and pages.user groups"
    echo
    echo "  Be sure to run ./cg-scripts/uaa/login.sh prior to executing this script"
    echo

    exit 1;
}

# Function to add user to pages.admin and pages.user groups
function add_user {
    USER=$1

    if [[ -z "${USER}" ]]; then

        echo "username not set!"
        usage

    else
        # adding user to pages.user group
        echo "adding ${USER} to pages.user group "
        uaac member add pages.user ${USER}

        # adding user to pages.admin group
        echo "adding ${USER} to pages.user group "
        uaac member add pages.admin ${USER}

        echo "${USER} has been add to pages.user and pages.admin groups"
    fi

}

# Function to remove user to pages.admin and pages.user groups
function remove_user {
    USER=$1

    if [[ -z "${USER}" ]]; then

        echo "username not set!"
        usage

    else
        # removing user from pages.user group
        echo "removing ${USER} from pages.user group "
        uaac member delete pages.user ${USER}

        # removing user from pages.admin group
        echo "removing ${USER} from pages.admin group "
        uaac member delete pages.admin ${USER}

        echo "${USER} has been removed from pages.user and pages.admin groups"
    fi

}

while getopts ":ar" opt; do
    case ${opt} in
        a)
          # calling add user function
          add_user ${2}
          ;;
        r)
          # calling remove user function
          remove_user ${2}
          ;;
        \?)
          usage
          exit 1;
          ;;
    esac
done
