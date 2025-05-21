#!/bin/bash

set -eu

pushd () {
  command pushd "$@" > /dev/null
}

popd () {
  command popd "$@" > /dev/null
}

uaa_login() {
  echo "Logging into UAA"
  this_directory=$(dirname "$0")
  pushd $this_directory
    ./login.sh
  popd
  echo " "
}

present_options() {
  if [ "$uaa_only" == "true" ]; then
    local in_credhub=($(credhub get -n ${credhub_key} -j | jq -r '.value | keys | .[]'))
    local in_uaa=($(uaac curl /identity-providers | awk '/BODY/{y=1;next}y' | jq -r '.[].originKey'))
    for idp in ${in_credhub[@]}; do
      in_uaa=( "${in_uaa[@]/$idp}" )
    done
    in_uaa=( "${in_uaa[@]/uaa}" )
    for v in "${in_uaa[@]}"; do
      if test "$v"; then
        idps+=("$v")
      fi
    done
  else
    local idps=($(credhub get -n ${credhub_key} -j | jq -r '.value | keys | .[]'))
  fi
  PS3='Which IDP would you like to delete: '
  select opt in "${idps[@]}" "Quit"
  do
    if [[ $opt == "Quit" ]]; then
      echo "Quitting..."
      exit
    elif [[ " ${idps[@]} " =~ " ${opt} " ]]; then
      echo "Selected: $opt"
      confirm $opt
    else
      echo "Invalid selection"
    fi
  done
}

confirm() {
  local idp=$1
  if [ "$uaa_only" == "true" ]; then
    PS3="Are you sure you want to delete $idp from UAA only? "
  else
    PS3="Are you sure you want to delete $idp? "
  fi
  select opt in "Yes" "No"
  do
    if [[ $opt == "Yes" ]]; then
      delete_idp $idp
    else
      echo "Exiting..."
      exit
    fi
  done
}

construct_import_file() {
  local json=$1
  echo "credentials: " > import.yml
  echo "- name: ${credhub_key}" >> import.yml
  echo "  type: json" >> import.yml
  echo "  value: $json" >> import.yml
}

delete_idp() {
  local idp=$1

  if [ "$uaa_only" != "true" ];then
    echo " "
    echo "Writing back up file to filesystem at ${PWD}/uaa-saml-providers-backup.json. You might want to back this up."
    credhub get -n ${credhub_key} -j | jq -r '.value' > uaa-saml-providers-backup.json
    echo "Done... REALLY, you may want to back this up off the jumpbox!"
    echo " "

    echo "Deleting IDP from credhub: $idp"
    length_before=$(credhub get -n ${credhub_key} -j | jq -r '.value | length')
    credhub get -n ${credhub_key} -j | jq -r '.value | del(."'"$idp"'")' > updated-uaa-saml-providers.json
    length_after=$(cat updated-uaa-saml-providers.json | jq -r '. | length')
    expected_length=$(($length_before - 1))
    updated_keys=$(cat updated-uaa-saml-providers.json | jq -r '. | keys | .[]')
    echo "Updated Keys: $updated_keys"
    if [[ $expected_length != $length_after ]] ||  [[ " ${updated_keys[@]} " =~ " ${idp} " ]]; then
      echo "An error occurred updating the json."
      echo "The IDP has not been deleted and credhub has not been updated."
      echo "Aborting..."
      exit 1
    fi
    json=$(cat updated-uaa-saml-providers.json)
    construct_import_file "$json"
    credhub import -f import.yml
    echo "IDP deleted from Credhub"
    echo " "
  fi

  echo "Deleting IDP from UAA: $idp"
  idp_id=$(uaac curl /identity-providers | awk '/BODY/{y=1;next}y' | jq -r '.[] | select(.originKey == "'$idp'") | .id')
  if [[ "$idp_id" == "" ]]; then
    echo "ERROR: Could not find the IDP id"
    exit 1
  fi

  uaac curl /identity-providers/${idp_id} -X DELETE
  echo "IDP deleted from UAA"
  echo " "

  echo "Done. Credhub changes will become permanent on the next UAA deployment."
  exit 0
}

usage() {
  echo "Usage: "
  echo "  $0 "
  echo " "
  echo "  Options: "
  echo "  --uaa-only Remove an IDPs that does not have metadata in credhub but is still listed in UAA"
  echo "  --help This message"
}

if [ $# -eq 0 ]; then
  uaa_only="false"
elif [ "$1" == "--uaa-only" ]; then
  uaa_only="true"
elif [ "$1" == "--help" ]; then
  usage
  exit
else
  usage
  exit 1
fi
environment_name="${BOSH_DIRECTOR_NAME,,}"
credhub_key=/bosh/cf-"${environment_name}"/uaa-saml-providers
uaa_login
this_directory=$(dirname "$0")
pushd $this_directory/../..
  present_options
popd