#!/usr/bin/env ruby
# Create a CSV of of service plans by space with associated contact info
# You must be authenticated to a CF API for this to work, as it uses
# "cf curl".

require 'json'
require 'csv'
require 'pp'
require_relative 'helpers'


def exempt_space?(space_name)
  space_name =~ /stag|dev|test|sandbox|\A(alan|yoz)\z/
end


def get_non_sandbox_spaces
  all_spaces = {}

  Helpers.cf_api_paginated('/v2/organizations').each do |org|
    next if org['entity']['name'].include? "sandbox"

    org_guid = org['metadata']['guid']
    Helpers.cf_api_paginated("/v2/organizations/#{org_guid}/spaces").each do |space|
      space_name = space['entity']['name']
      next if exempt_space?(space_name)
      space_guid = space['metadata']['guid']
      all_spaces[space_guid] = space_name
    end
  end

  puts "All spaces #{all_spaces.length}"

  all_spaces
end


def get_all_services
  services = {}
  Helpers.cf_api_paginated('/v2/services').each do |service|
    services[service['metadata']['guid']] = service['entity']['description']
  end

  services
end

def get_used_service_plans(services, spaces)
  service_plans = {}

  Helpers.cf_api_paginated('/v2/service_plans').each do |service_plan|
    service_plans[service_plan['metadata']['guid']] = {
      'service_guid' => service_plan['entity']['service_guid'],
      'expanded_name' => services[service_plan['entity']['service_guid']] + ' : ' + service_plan['entity']['name'],
      'service_instance_count' => 0
    }
  end

  Helpers.cf_api_paginated('/v2/service_instances').each do |service_instance|
    if spaces[service_instance['entity']['space_guid']]
      service_plans[service_instance['entity']['service_plan_guid']]['service_instance_count'] += 1
    end
  end

  # reduce the service plans hash to only those plans that have active instances, and sort them
  # in descenting order
  service_plans.delete_if {| k, v | v['service_instance_count'] == 0 }
  service_plans = service_plans.sort_by { |k, v| v['service_instance_count'].to_i }.reverse
end


def get_org_managers(org_guid)
  managers = []

  Helpers.cfmunge("/v2/organizations/#{org_guid}/managers").each do |m|
    next if !m["entity"]["username"]
    managers.push(m["entity"]["username"])
  end

  managers.join(",")

end

def get_space_managers(space_guid)
  managers = []

  Helpers.cfmunge("/v2/spaces/#{space_guid}/managers").each do |m|
    username = m["entity"]["username"]
    next if !username
    managers.push(username)
  end

  managers.join(",")
end


def get_space_developers(space_guid)
  developers = []

  Helpers.cfmunge("/v2/spaces/#{space_guid}/developers").each do |m|
    username = m["entity"]["username"]
    next if !username
    developers.push(username)
  end

  developers.join(",")
end

def get_service_plan_headers(service_plans)
  service_plans.map do |k, v|
    v['expanded_name']
  end
end

def get_space_service_instances(space_guid, service_plans)
  service_instances = Hash.new(0)

  Helpers.cfmunge("/v2/spaces/#{space_guid}/service_instances").each do |service_instance|
    plan_guid = service_instance['entity']['service_plan_guid']
    service_instances[plan_guid] += 1
  end

  service_plans.map do |k, v|
    if service_instances.key?(k)
      "#{service_instances[k]}"
    else
      "0"
    end
  end
end


@spaces = get_non_sandbox_spaces()
@services = get_all_services()
@service_plans = get_used_service_plans(@services, @spaces)

stamp = Time.now.to_i

CSV.open("cf-orgs-services-managers-#{stamp}.csv", "wb") do |csv|
  csv << ["Org","Org Managers","Space", "Space Developers", "Space Developers"] + get_service_plan_headers(@service_plans)

  Helpers.cf_api_paginated('/v2/organizations?order-by=name').each do |org|
    next if org['entity']['name'].include? "sandbox"

    org_name = org['entity']['name']
    org_guid = org['metadata']['guid']
    org_managers = get_org_managers(org_guid)

    Helpers.cf_api_paginated("/v2/organizations/#{org_guid}/spaces").each do |space|
      next if exempt_space?(space['entity']['name'])

      space_name = space['entity']['name']
      space_guid = space['metadata']['guid']
      space_managers = get_space_managers(space_guid)
      space_developers = get_space_developers(space_guid)

      row = [org_name, org_managers, space_name, space_managers, space_developers]
      row += get_space_service_instances(space_guid, @service_plans)
      csv << row
    end
  end
end
