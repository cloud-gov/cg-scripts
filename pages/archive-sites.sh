#! /bin/bash 

set -e

function fail() {
	echo $@
	exit 1
}

function mirror() {
	set -x
	local site=$1
	 wget --recursive \
	       --directory-prefix="$PREFIX" \
           --page-requisites \
           --adjust-extension \
           --span-hosts \
           --convert-links \
           --domains $site \
           --no-parent https://www.$site
	set +x
}

TARGET="$HOME/Google Drive/Shared drives/Cloud.gov Public/IDCDB-archive"

[ -d "$TARGET" ] || fail "Cannot access Google Drive target $TARGET"

TIMESTAMP=$(date "+%Y%m%d-%H%M")

PREFIX="$TARGET/$TIMESTAMP" 
mkdir -p "$PREFIX" || fail "Unable to create the target directory $PREFIX"

#for S in cdo.gov cfo.gov paymentaccuracy.gov cio.gov coffa.gov evaluation.gov fpc.gov statspolicy.gov fcsm.gov; do 
for S in cfo.gov paymentaccuracy.gov cio.gov coffa.gov evaluation.gov fpc.gov statspolicy.gov fcsm.gov; do 
  echo "=============="
  echo "STARTING SITE: $S"
  echo "=============="
  sleep 1
  mirror $S || echo "exit status $?, continuing"
done
