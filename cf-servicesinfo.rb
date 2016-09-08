#!/usr/bin/env ruby
# Create a CSV of of service plans by space with associated contact info
# You must be authenticated to a CF API for this to work, as it uses
# "cf curl".

require 'rubygems'
require 'json'
require 'csv'
require 'pp'

def cfmunge(url)
  raw = %x(/usr/local/bin/cf curl "#{url}")
  return cooked = JSON.parse(raw)["resources"]
end

def exempt_space(space_name)

	if space_name.include?('stag') ||
		space_name.include?('dev') ||
		space_name.include?('test') ||
		space_name.include?('sandbox') ||
		space_name == 'alan' ||
		space_name == 'yoz'
		return true
	end

	return false
end


def get_non_sandbox_spaces()

	all_spaces = Hash.new

	cfmunge('/v2/organizations?results-per-page=100').each do |org|
		next if org['entity']['name'].include? "sandbox"

		page = 1
		more_spaces = true
		while more_spaces
			spaces = cfmunge("/v2/organizations/#{org['metadata']['guid']}/spaces?page=#{page}&results-per-page=100")
			if spaces.length > 0
				spaces.each do |space|
					next if exempt_space(space['entity']['name'])
					all_spaces[space['metadata']['guid']] = space['entity']['name']
				end
			else
				more_spaces = false
			end
			page += 1
		end
	end

	puts "All spaces #{all_spaces.length}"

	all_spaces

end


def get_all_services

	services = Hash.new
	cfmunge('/v2/services?results-per-page=100').each do |service|
		services[service['metadata']['guid']] = service['entity']['description']
	end

	services
end

def get_used_service_plans(services, spaces)

	service_plans = Hash.new

	cfmunge('/v2/service_plans?results-per-page=100').each do |service_plan|
		service_plans[service_plan['metadata']['guid']] = {
			'service_guid' => service_plan['entity']['service_guid'],
			'expanded_name' => services[service_plan['entity']['service_guid']] + ' : ' + service_plan['entity']['name'],
			'service_instance_count' => 0
		}
	end

	page = 1
	while page < 3
		cfmunge("/v2/service_instances?page=#{page}&results-per-page=100").each do |service_instance|
			if spaces[service_instance['entity']['space_guid']]
				service_plans[service_instance['entity']['service_plan_guid']]['service_instance_count'] += 1
			end
		end
		page += 1
	end

	# reduce the service plans hash to only those plans that have active instances, and sort them
	# in descenting order
	service_plans.delete_if {| k, v | v['service_instance_count'] == 0 }
	service_plans = service_plans.sort_by { |k, v| v['service_instance_count'].to_i }.reverse

end


def get_org_managers(org_guid)

  managers = Array.new

  cfmunge("/v2/organizations/#{org_guid}/managers").each do |m|
  	next if !m["entity"]["username"]
    managers.push(m["entity"]["username"])
  end

  managers.join(",")

end

def get_space_managers(space_guid)

  managers = Array.new

  cfmunge("/v2/spaces/#{space_guid}/managers").each do |m|
  	next if !m["entity"]["username"]
    managers.push(m["entity"]["username"])
  end

  managers.join(",")

end


def get_space_developers(space_guid)

  developers = Array.new

  cfmunge("/v2/spaces/#{space_guid}/developers").each do |m|
  	next if !m["entity"]["username"]
    developers.push(m["entity"]["username"])
  end

  developers.join(",")

end

def get_service_plan_headers(service_plans)

	headers = Array.new
	service_plans.each do |k, v|
		headers.push(v['expanded_name'])
	end

	headers
end

def get_space_service_instances(space_guid, service_plans)

	service_instances = Hash.new

	cfmunge("/v2/spaces/#{space_guid}/service_instances").each do |service_instance|
		if service_instances.key?(service_instance['entity']['service_plan_guid'])
			service_instances[service_instance['entity']['service_plan_guid']] += 1
		else
			service_instances[service_instance['entity']['service_plan_guid']] = 1
		end
	end

	instances = Array.new
	service_plans.each do |k, v|
		if service_instances.key?(k)
			instances.push("#{service_instances[k]}")
		else
			instances.push("0")
		end
	end

	instances

end


@spaces = get_non_sandbox_spaces()
@services = get_all_services()
@service_plans = get_used_service_plans(@services, @spaces)

stamp = Time.now.to_i

CSV.open("cf-orgs-services-managers-#{stamp}.csv", "wb") do |csv|
  csv << ["Org","Org Managers","Space", "Space Developers", "Space Developers", "Space GUID"] + get_service_plan_headers(@service_plans)

	cfmunge('/v2/organizations?results-per-page=100&order-by=name').each do |org|
		next if org['entity']['name'].include? "sandbox"

		org_name = org['entity']['name']
		org_managers = get_org_managers(org['metadata']['guid'])

		cfmunge("/v2/organizations/#{org['metadata']['guid']}/spaces").each do |space|
			next if exempt_space(space['entity']['name'])

			space_name = space['entity']['name']
			space_managers = get_space_managers(space['metadata']['guid'])
			space_developers = get_space_developers(space['metadata']['guid'])

			row = ["#{org_name}","#{org_managers}","#{space_name}", "#{space_managers}", "#{space_developers}", "#{space['metadata']['guid']}"]
			row += get_space_service_instances(space['metadata']['guid'], @service_plans)
			csv << row
		end
	end
end
