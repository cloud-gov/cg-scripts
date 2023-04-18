#!/usr/bin/env bash

echo "processing repo: $1"

TMPDIR=$(mktemp -d)

pushd "$TMPDIR" || exit
  git clone "https://github.com/cloud-gov/$1.git" .
  git checkout master
  git checkout -b main
  echo "created main branch from master branch"
  git push -u origin main
  echo "pushed main branch"
popd || exit

rm -rf "$TMPDIR"

gh repo edit "cloud-gov/$1" --default-branch main
echo "Set default branch to main for $1"
