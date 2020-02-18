#!/bin/bash -euo pipefail

BRANCH=pdb/portable-test # set to 'master' when merged

tempname=`basename $0`
TMPDIR=`mktemp -d /tmp/${tempname}.XXXXXX`
if [ $? -ne 0 ]; then
  echo "$0: Can't create temp dir, $TMPDIR, exiting..."
  exit 1
fi

for f in seekrets.bats test_helper.bash; do
  curl -s -o $TMPDIR/$f https://raw.githubusercontent.com/18F/laptop/$BRANCH/test/$f
done

export LOCAL_AUDIT=true
bats --tap $TMPDIR/seekrets.bats
