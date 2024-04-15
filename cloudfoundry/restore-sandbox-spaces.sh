#!/bin/bash

INPUT_FILE=$1

ADMIN=$(cf target | grep -i user | awk '{print $2}')

while read -r line; do
  IFS=';' read -r -a array <<< "$line"
  SPACE_NAME="${array[0]}"
  ORG_NAME="${array[1]}"
  DEVELOPERS="${array[2]}"
  MANAGERS="${array[3]}"

  echo "recreating sandbox space $SPACE_NAME in org $ORG_NAME"

  cf create-space "$SPACE_NAME" -o "$ORG_NAME" -q "sandbox_quota"
  
  if [[ -n "$DEVELOPERS" ]]; then
    echo "recreating sandbox space developers in space $SPACE_NAME, org $ORG_NAME"
    for developer in $DEVELOPERS; do
      cf set-space-role "$developer" "$ORG_NAME" "$SPACE_NAME" SpaceDeveloper
    done
  fi

  if [[ -n "$MANAGERS" ]]; then
    echo "recreating sandbox space managers in space $SPACE_NAME, org $ORG_NAME"
    for manager in $MANAGERS; do
      cf set-space-role "$manager" "$ORG_NAME" "$SPACE_NAME" SpaceManager
    done
  fi

  # creator added by default - undo
  cf unset-space-role "$ADMIN" "$ORG_NAME" "$SPACE_NAME" SpaceManager
  cf unset-space-role "$ADMIN" "$ORG_NAME" "$SPACE_NAME" SpaceDeveloper

  printf "\n"

done < "$INPUT_FILE"
