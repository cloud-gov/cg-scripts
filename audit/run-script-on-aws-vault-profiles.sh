#!/bin/bash

function usage {
  echo -e "
  Usage

  ./$( basename "$0" ) path/to/script destination-folder [profile-prefix] [--help, -h]

  Run a script using all the aws-vault profiles matching a prefix. Writes from script invocations
  to the specified folder.

  Optional argument for prefix to use for matching aws-vault profiles. Default is \"gov-\"
  "
}

while getopts ":h" opt; do
  case ${opt} in
    h )
        usage
        exit 0
        ;;
    * )
        usage
        exit 0
        ;;
  esac
done

if [ -z "$1" ]
  then
    echo "You must supply a script name"
    usage
    exit 1
fi
SCRIPT=$1

if [ -z "$2" ]
  then
    echo "You must supply an output destination"
    usage
    exit 1
fi
DESTINATION=$2

PROFILE_PREFIX=${3:-gov-}

for profile in $(aws-vault ls --profiles | grep "^$PROFILE_PREFIX"); do
  SCRIPT_FILENAME=$(basename "$SCRIPT")
  DESTINATION_FILE=$(echo "$SCRIPT_FILENAME" | sed -e 's/\//-/g;s/\./-/g')
  aws-vault exec "$profile" -- "$SCRIPT" > "$DESTINATION/$profile-$DESTINATION_FILE.txt" 2>&1
done