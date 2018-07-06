#!/bin/sh
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

START=$(date -v -15d +"%Y-%m-%dT%H:%M:%SZ")
echo "pulling cloudtrail from a bit over 2 weeks ago ($START)"

aws cloudtrail lookup-events --no-paginate --start-time "$START" --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin > /tmp/consolefoo.$$

echo "============ Console users (run 'aws cloudtrail lookup-events --no-paginate --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin' for details)"
cat /tmp/consolefoo.$$ | jq -r .Events[].Username | sort | uniq -c
echo

echo "============ Console events for Administrator (should be none)"
cat /tmp/consolefoo.$$ | jq -r '.Events[] | select(.Username == "Administrator")' > /tmp/admin.$$
cat /tmp/consolefoo.$$ | jq -r '.Events[] | select(.Username != "..*") | .CloudTrailEvent' | \
	jq -r 'select(.userIdentity.userName == "Administrator")' >> /tmp/admin.$$
cat /tmp/admin.$$
echo

rm -f /tmp/admin.$$
rm -f /tmp/consolefoo.$$

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
	echo "======================= non-terraform events for $event_name (should be none)"
	aws cloudtrail lookup-events --no-paginate --start-time "$START" --lookup-attributes AttributeKey=EventName,AttributeValue="$event_name" | \
		jq -r '.Events[] | .CloudTrailEvent' | \
		jq -r 'select(if ((.userIdentity.accessKeyId | startswith("ASIA")) and (.sourceIPAddress | startswith("96.127") or startswith("52.222")) and (.userIdentity.principalId | test("[A-Z0-9]{21}:i-[0-9a-z]{17}"))) then false else true end)'
	echo
done

