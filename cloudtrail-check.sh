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

if [ "$1" = "-a" ] ; then
	AUDITMODE=true
fi
RETURN=0

START=$(date -v -15d +"%Y-%m-%dT%H:%M:%SZ")
echo "pulling cloudtrail from a 15 days ago so that 2 week audits will always overlap a bit ($START)"

aws cloudtrail lookup-events --no-paginate --start-time "$START" --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin > /tmp/consolefoo.$$

echo "============ Console logins per user"
echo "============ Run 'aws cloudtrail lookup-events --no-paginate --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin'"
echo "============ for details on the logins if something seems unusual about the users or the number of times they logged in."
cat /tmp/consolefoo.$$ | jq -r .Events[].Username | sort | uniq -c
echo

cat /tmp/consolefoo.$$ | jq -r '.Events[] | select(.Username == "Administrator")' > /tmp/admin.$$
cat /tmp/consolefoo.$$ | jq -r '.Events[] | select(.Username != "..*") | .CloudTrailEvent' | \
	jq -r 'select(.userIdentity.userName == "Administrator")' >> /tmp/admin.$$
if [ -s /tmp/admin.$$ ] ; then
	echo "============ Found console events for Administrator: investigate"
	cat /tmp/admin.$$
	RETURN=1
	echo
elif [ "$AUDITMODE" = "true" ] ; then
	echo "============ Checking console events for Administrator"
	echo "none found:  no action required"
	echo
fi

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
	rm -rf /tmp/eventinfo.$$
	aws cloudtrail lookup-events --no-paginate --start-time "$START" --lookup-attributes AttributeKey=EventName,AttributeValue="$event_name" | \
		jq -r '.Events[] | .CloudTrailEvent' | \
		jq -r 'select(if ((.userIdentity.accessKeyId | startswith("ASIA")) and (.sourceIPAddress | startswith("96.127") or startswith("52.222")) and (.userIdentity.principalId | test("[A-Z0-9]{21}:i-[0-9a-z]{17}"))) then false else true end)' > /tmp/eventinfo.$$
	if [ -s /tmp/eventinfo.$$ ] ; then
		echo "======================= found non-terraform events for $event_name: investigate"
		cat /tmp/eventinfo.$$
		RETURN=1
		echo
	elif [ "$AUDITMODE" = "true" ] ; then
		echo "============ checking non-terraform events for $event_name"
		echo "none found:  no action required"
		echo
	fi
	rm -rf /tmp/eventinfo.$$
done

exit $RETURN

