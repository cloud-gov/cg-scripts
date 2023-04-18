#!/usr/bin/env bash

if [ -z "$1" ]; then
  echo "Repo name is required as first argument to script"
  exit 1
fi

OLD_BRANCH=${2:-master}
NEW_BRANCH=${3:-main}

# Requires https://github.com/ethomson/retarget_prs
npx retarget_prs --token "$PAT_TOKEN" "$1" "$OLD_BRANCH" "$NEW_BRANCH"
