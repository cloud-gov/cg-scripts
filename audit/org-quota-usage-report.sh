#!/bin/bash

orgs_json=$(cf curl /v3/organizations?per_page=5000)

org_names=$(echo "$orgs_json" | jq -r '.resources[].name')

echo "Org Name, Org GUID, Org Created, Org Updated, Quota Name, Quota GUID, Quota Created, Quota Updated, Quota Memory (MB), Used Memory (MB)"

for org_name in $org_names; do
  org_json=$(echo "$orgs_json" | jq -r '.resources[] | select(.name == "'"$org_name"'")')
  org_guid=$(echo "$org_json" | jq -r '.guid')
  org_created=$(echo "$org_json" | jq -r '.created_at')
  org_updated=$(echo "$org_json" | jq -r '.updated_at')
  
  quota_guid=$(echo "$org_json" | jq -r '.relationships.quota.data.guid')
  quota_json=$(cf curl /v3/organization_quotas/${quota_guid})
  quota_name=$(echo "$quota_json" | jq -r '.name')
  quota_created=$(echo "$quota_json" | jq -r '.created_at')
  quota_updated=$(echo "$quota_json" | jq -r '.updated_at')
  quota_memory=$(echo "$quota_json" | jq -r '.apps.total_memory_in_mb')

  usage_json=$(cf curl /v3/organizations/${org_guid}/usage_summary)
  usage_memory=$(echo "$usage_json" | jq -r '.usage_summary.memory_in_mb')

  echo "${org_name}, ${org_guid}, ${org_created}, ${org_updated}, ${quota_name}, ${quota_guid}, ${quota_created}, ${quota_updated}, ${quota_memory}, ${usage_memory}"
done
