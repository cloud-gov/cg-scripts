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
    echo "      -a     :     add user to pages.admin group"
    echo "      -u     :     add user to pages.user group"
    echo "      -r     :     remove user from pages.admin group"
    echo "      -d     :     remove user from pages.user group"
    echo
    echo "  Be sure to run ./cg-scripts/uaa/login.sh prior to executing this script"
    echo

    exit 1;
}

# Function to add user to pages.user group
function add_user {
    USER=$1

    if [[ -z "${USER}" ]]; then

        echo "username not set!"
        usage

    else
        # adding user to pages.user group
        echo "adding ${USER} to pages.user group "
        uaac member add pages.user ${USER}

        echo "${USER} has been add to pages.user group"
    fi

}

# Function to add user to pages.admin group
function add_admin {
       USER=$1

    if [[ -z "${USER}" ]]; then

        echo "username not set!"
        usage

    else
    
        # adding user to pages.admin group
        echo "adding ${USER} to pages.admin group "
        uaac member add pages.admin ${USER}

        echo "${USER} has been add to pages.admin group"
    fi

}

# Function to remove user from pages.user group
function remove_user {
    USER=$1

    if [[ -z "${USER}" ]]; then

        echo "username not set!"
        usage

    else
        # removing user from pages.user group
        echo "removing ${USER} from pages.user group "
        uaac member delete pages.user ${USER}

        echo "${USER} has been removed from pages.user group"
    fi

}

# Function to remove user from pages.admin group
function remove_admin {
    USER=$1

    if [[ -z "${USER}" ]]; then

        echo "username not set!"
        usage

    else

        # removing user from pages.admin group
        echo "removing ${USER} from pages.admin group "
        uaac member delete pages.admin ${USER}

        echo "${USER} has been removed from pages.admin group"
    fi

}

options_not_set="true"

while getopts ":aurd" opt; do
    case ${opt} in
        a)
          # calling add admin function
          add_admin ${2}
          ;;
        u)
          # calling add user function
          add_user ${2}
          ;;
        r)
          # calling remove user function
          remove_admin ${2}
          ;;
        d)
          # calling remove user function
          remove_user ${2}
          ;;
        \?)
          usage
          exit 1;
          ;;
    esac
    options_not_set="false"
done

# checking if options is set 
[[ "${options_not_set}" = "true" ]] && { echo "Option not set"; usage; exit 1; }



