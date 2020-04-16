#!/usr/bin/env bash

# TODO: rewrite in not-bash.
#
# This script is here to automate (as much as possible) the tasks in
# https://cloud.gov/docs/ops/maintenance-list/#review-aws-cloudtrail-events
#
# authorized events will include:
#   a user name like i-17deadbeef1234567
#   a source IP address within AWS.
#   an AWS access key starting with ASIA
#
# XXX The source IP range is kind of janky.  It would be better if this
#     pulled dynamically from AWS and also if we handled cidr notation
#     properly.  But these two ranges seem to work for govcloud right now.

set -e

if [ "$1" = "-a" ] ; then
  AUDITMODE=true
fi
RETURN=0

CONSOLE="/tmp/consolefoo.$$"
ADMIN="/tmp/admin.$$"

START=$(/bin/date -v -15d +"%Y-%m-%dT%H:%M:%SZ")
echo "pulling cloudtrail from a 15 days ago so that 2 week audits will always overlap a bit ($START)"

aws cloudtrail lookup-events --no-paginate --start-time "$START" --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin > "$CONSOLE"

echo "============ Console logins per user"
echo "============ Run 'aws cloudtrail lookup-events --no-paginate --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin'"
echo "============ for details on the logins if something seems unusual about the users or the number of times they logged in."
cat "$CONSOLE" | jq -r .Events[].Username | sort | uniq -c
echo

cat "$CONSOLE" | jq -r '.Events[] | select(.Username == "Administrator")' > "$ADMIN"
cat "$CONSOLE" | jq -r '.Events[] | select(.Username != "..*") | .CloudTrailEvent' | \
  jq -r 'select(.userIdentity.userName == "Administrator")' >> "$ADMIN"
if [ -s "$ADMIN" ] ; then
  echo "============ Found console events for Administrator: investigate"
  cat "$ADMIN"
  RETURN=1
  echo
elif [ "$AUDITMODE" = "true" ] ; then
  echo "============ Checking console events for Administrator"
  echo "none found:  no action required"
  echo
fi

rm -f "$ADMIN"
rm -f "$CONSOLE"

EVENTNAMES="
  DeleteTrail
  UpdateTrail
  ModifyVpcAttribute
  PutUserPolicy
  PutRolePolicy
  RevokeSecurityGroupEgress
  RevokeSecurityGroupIngress
  AuthorizeSecurityGroupEgress
  AuthorizeSecurityGroupIngress
  CreatePolicy
  CreateSecurityGroup
"

for event_name in $EVENTNAMES ; do
  EVENT="/tmp/eventinfo.$$"
  rm -rf "$EVENT"
  # We're making the assumption that any `CreatePolicy` call from the s3-broker
  # is normal
  aws cloudtrail lookup-events --no-paginate --start-time "$START" --lookup-attributes AttributeKey=EventName,AttributeValue="$event_name" \
    | jq -r '.Events[] | .CloudTrailEvent' \
    | jq -r 'select(((.userIdentity.accessKeyId | startswith("ASIA")) and (.sourceIPAddress | startswith("96.127") or startswith("52.222")) and (.userIdentity.principalId | test("[A-Z0-9]{21}:i-[0-9a-z]{17}")))|not)' \
    | jq -r 'select((.userIdentity.userName == "cg-s3-broker") and (.eventName == "CreatePolicy")|not)' \
    > "$EVENT"
  if [ -s "$EVENT" ] ; then
    echo "======================= found non-terraform events for $event_name: investigate"
    cat "$EVENT"
    RETURN=1
    echo
  elif [ "$AUDITMODE" = "true" ] ; then
    echo "============ checking non-terraform events for $event_name"
    echo "none found:  no action required"
    echo
  fi
  rm -rf "$EVENT"
done

exit $RETURN
