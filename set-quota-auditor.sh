# This script walks through each org in a Cloud Foundry instance setting
# OrgAuditor and SpaceAuditor permissions at each level.
#
# Usage:
#
#  set-quota-auditor.sh AUDIT_USER
set -e

USER_EMAIL=$1

# Strip the host portion of the email supplied.
USER_NAME="${USER_EMAIL%%@*}"

cf orgs \
  | awk 'm;/^name/{m=1}' \
  | while read ORG_NAME
      do cf set-org-role $USER_NAME $ORG_NAME OrgAuditor
      cf target -o $ORG_NAME
      cf spaces \
      | awk 'm;/^name/{m=1}' \
      | while read SPACE_NAME
          do cf set-space-role $USER_NAME $ORG_NAME $SPACE_NAME SpaceAuditor
        done
    done
