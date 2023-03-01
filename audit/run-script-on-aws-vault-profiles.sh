#!/bin/bash

function usage {
  echo -e "
  Usage

  ./$( basename "$0" ) -s path/to/script -o destination-folder -p [profile-prefix] -d [duration] [--help, -h] [optional list of profiles]

  Examples:

  ./$( basename "$0" ) -s ./audit-iam.sh -o ~/Downloads -p \"com-\"
  ./$( basename "$0" ) -s ./audit-iam.sh -o ~/Downloads profile-1,profile-2

  options:

  $0 -h                         Display this help message.
  $0 -s                         Path to script to run against aws-vault profiles
  $0 -o                         Destination folder for output from script invocations
  $0 -p                         Optional - argument for prefix to use for matching aws-vault profiles. Default is \"gov-\"
  $0 -d                         Optional - duration to use for lifetime of aws-vault credentials. If you need to run a script that will take a long time to execute,
                                specify a long duration like \"8h\" so that credentials don't expire during execution. Default is \"1h\".

  Run a script using all the aws-vault profiles matching a prefix. Writes from script invocations
  to the specified folder.
  "
}

PROFILE_PREFIX="gov-"
DURATION="1h"

while getopts ":hs:o:p:d:" opt; do
  case ${opt} in
    h )
        usage
        exit 0
        ;;
    s )
        SCRIPT=$OPTARG
        ;;
    o )
        DESTINATION=$OPTARG
        ;;
    p )
        PROFILE_PREFIX=$OPTARG
        ;;
    d )
        DURATION="8h"
        ;;
    * )
        usage
        exit 0
        ;;
  esac
done
shift $((OPTIND -1))

if [ -z "$SCRIPT" ]
  then
    echo "Error: You must supply a script name"
    usage
    exit 1
fi

if [ -z "$DESTINATION" ]
  then
    echo "Error: You must supply an output destination"
    usage
    exit 1
fi

PROFILES=$(aws-vault ls --profiles | grep "^$PROFILE_PREFIX")
if [ -n "$1" ]
  then
    PROFILES=${1//,/ }
fi

export AWS_PAGER=''

for profile in $PROFILES; do
  SCRIPT_FILENAME=$(basename "$SCRIPT")
  DESTINATION_FILE=$(echo "$SCRIPT_FILENAME" | sed -e 's/\//-/g;s/\./-/g')
  # initial command just to display prompt for MFA, if necessary. prompt for MFA comes from stderr and will
  # be swallowed by the next command actually running the script, since it redirects stderr to stdout and writes
  # to a file
  aws-vault exec "$profile" -d "$DURATION" -- aws sts get-caller-identity
  # run script using aws-vault profile and redirect stderr to stdout, with stdout written to a file
  aws-vault exec "$profile" -d "$DURATION" -- "$SCRIPT" > "$DESTINATION/$profile-$DESTINATION_FILE.txt" 2>&1
done