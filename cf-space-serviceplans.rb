#!/usr/bin/env ruby
# 2016 Dan Shick for 18F/GSA
#
# You must be authenticated to a CF API for this to work, as it uses
# "cf curl".

require 'pp'
require_relative 'helpers'


def get_all_services
  services = Hash.new
  Helpers.cfmunge('/v2/services?results-per-page=100').each do |service|
    services[service['metadata']['guid']] = service['entity']['description']
  end

  services
end

def get_used_service_plans(services)
  service_plans = Hash.new

  Helpers.cfmunge('/v2/service_plans?results-per-page=100').each do |service_plan|
    service_plans[service_plan['metadata']['guid']] = {
      'service_guid' => service_plan['entity']['service_guid'],
      'expanded_name' => services[service_plan['entity']['service_guid']] + ' : ' + service_plan['entity']['name'],
      'service_instance_count' => 0
    }
  end

  page = 1
  while page < 3
    Helpers.cfmunge("/v2/service_instances?page=#{page}&results-per-page=100").each do |service_instance|
      service_plans[service_instance['entity']['service_plan_guid']]['service_instance_count'] += 1
    end
    page += 1
  end

  # reduce the service plans hash to only those plans that have active instances, and sort them
  # in descenting order
  service_plans.delete_if {| k, v | v['service_instance_count'] == 0 }
  service_plans = service_plans.sort_by { |k, v| v['service_instance_count'] }.reverse

end

def get_service(service_guid)
  Helpers.cfmunge("/v2/services/#{service_guid}")
end


def get_service_plan(service_plan_guid)
  Helpers.cfmunge("/v2/service_plans/#{service_plan_guid}")
end

def get_org_managers(org_guid)
  managers = []

  Helpers.cfmunge("/v2/organizations/#{org_guid}/managers").each do |m|
    managers.push(m["entity"]["username"])
  end

  managers.join(",")
end

def get_space_managers(space_guid)
  developers = []

  Helpers.cfmunge("/v2/spaces/#{space_guid}/developers").each do |m|
    developers.push(m["entity"]["username"])
  end

  developers.join(",")

end

def get_service_plan_headers(service_plans)
  headers = []
  service_plans.each do |k, v|
    headers.push(v['expanded_name'])
  end

  headers
end

def get_space_service_instances(space_guid, service_plans)
  service_instances = Hash.new

  Helpers.cfmunge("/v2/spaces/#{space_guid}/service_instances").each do |service_instance|
    if service_instances.key?(service_instance['entity']['service_plan_guid'])
      service_instances[service_instance['entity']['service_plan_guid']] += 1
    else
      service_instances[service_instance['entity']['service_plan_guid']] = 0
    end
  end

  instances = []
  service_plans.each do |k, v|
    if service_instances.key?(k)
      instances.push("#{service_instances[k]}")
    else
      instances.push("0")
    end
  end

  instances
end

def display_space_services(space_guid)
  Helpers.cfmunge("/v2/spaces/#{space_guid}/service_instances").each do |service_instance|
    service_plan = get_service_plan(service_instance['entity']['service_plan_guid'])
    service = get_service(service_plan['entity']['service_guid'])
    puts "#{service['entity']['description']} #{service_plan['entity']['name']} : #{service_plan['entity']['description']}"
  end
end

display_space_services('bd4bbca2-f3f5-4ba6-808d-6e42469201b0')
