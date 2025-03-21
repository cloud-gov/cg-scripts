#! /bin/bash 

# Periodically archive GSA "MY" sites to Drive for GSA retention purposes
# for IDCDB: OGP IT Services Branch

# This script uses `wget` to mirror the sites in question, 
# and rewrites links so they're internally consistent
# Assumes you have Google Drive installed so you can save content to a common location
# See also: https://cloud-gov-new.zendesk.com/agent/tickets/11194

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

which wget || fail "Need to install wget, e.g., 'brew install wget'"

TARGET="$HOME/Google Drive/Shared drives/Cloud.gov Public/IDCDB-archive"

[ -d "$TARGET" ] || fail "Cannot access Google Drive target $TARGET"

TIMESTAMP=$(date "+%Y%m%d")

PREFIX="$TARGET/$TIMESTAMP" 
mkdir -p "$PREFIX" || fail "Unable to create the target directory $PREFIX"

for S in cdo.gov cfo.gov paymentaccuracy.gov cio.gov coffa.gov evaluation.gov fpc.gov statspolicy.gov fcsm.gov; do 
  echo "=============="
  echo "STARTING SITE: $S"
  echo "=============="
  sleep 1
  mirror $S || echo "exit status $?, continuing"
done
