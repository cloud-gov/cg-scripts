#!/bin/bash

function usage {
  echo -e "
  Usage

  ./$( basename "$0" ) -s path/to/script -d destination-folder -p [profile-prefix] [--help, -h] [optional list of profiles]

  Examples:

  ./$( basename "$0" ) -s ./audit-iam.sh -d ~/Downloads -p \"com-\"
  ./$( basename "$0" ) -s ./audit-iam.sh -d ~/Downloads profile-1,profile-2

  options:

  $0 -h                         Display this help message.
  $0 -s                         Path to script to run against aws-vault profiles
  $0 -d                         Destination folder for output from script invocations
  $0 -p                         Optional argument for prefix to use for matching aws-vault profiles. Default is \"gov-\"

  Run a script using all the aws-vault profiles matching a prefix. Writes from script invocations
  to the specified folder.
  "
}

PROFILE_PREFIX="gov-"

while getopts ":hs:d:p:" opt; do
  case ${opt} in
    h )
        usage
        exit 0
        ;;
    s )
        SCRIPT=$OPTARG
        ;;
    d )
        DESTINATION=$OPTARG
        ;;
    p )
        PROFILE_PREFIX=$OPTARG
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

for profile in $PROFILES; do
  SCRIPT_FILENAME=$(basename "$SCRIPT")
  DESTINATION_FILE=$(echo "$SCRIPT_FILENAME" | sed -e 's/\//-/g;s/\./-/g')
  aws-vault exec "$profile" -- "$SCRIPT" > "$DESTINATION/$profile-$DESTINATION_FILE.txt" 2>&1
done