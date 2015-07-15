#!/usr/bin/env bash
set -e

# Run this script in the `cf-release` folder
# Usage:
#   template-changes.sh v210 v212
# Output is stored in the active directory

git checkout master
./update

FROM_REV=$1
TO_REV=$2

OUT=changes-$FROM_REV-$TO_REV.log

echo "Changes in cf-release templates from $FROM_REV to $TO_REV" > $OUT

# Get changes in the spec manifests
git diff $FROM_REV..$TO_REV spec/fixtures/aws/*.yml.erb >> $OUT

# Get changes on canonical templates
git diff $FROM_REV..$TO_REV templates/*.yml >> $OUT

# Get changes on job templates
git diff $FROM_REV..$TO_REV jobs/**/templates/*.yml.erb >> $OUT

echo "Find changes in $OUT"
