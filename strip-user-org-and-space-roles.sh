#!/bin/bash -ex

# User input
# cmd.sh USER ORG SPACE

USER="$1"
ORG="$2"
ORGROLE="OrgManager"

cf org-users $ORG
cf unset-org-role $USER $ORG $ORGROLE

SPACE="$3"
SPACEROLE="SpaceManager"

cf space-users $ORG $SPACE

cf unset-space-role $USER $ORG $SPACE $SPACEROLE
SPACEROLE="SpaceDeveloper"
cf unset-space-role $USER $ORG $SPACE $SPACEROLE
SPACEROLE="SpaceAuditor"
cf space-users $ORG $SPACE
