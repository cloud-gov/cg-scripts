#!/usr/bin/env ruby
# 2016 Dan Shick for 18F/GSA
#
# cf-orgsinfo -- outputs a CSV of Cloud Foundry organizations, GUIDs, associated services and all org managers. You must be authenticated to a CF API for this to work, as it uses `cf curl`. Execute with `bundle exec ruby cf-orgsinfo.rb`.

require 'csv'
require 'parallel'
require 'set'
require_relative 'helpers'


def user_provided_service_instance?(bind)
  bind['entity']['service_instance_url'].match('user_provided_service_instances')
end

# for each app, get its service bindings and use them to create a list of bound services not user-provided
def bound_services(app_guid)
  results = Set.new
  Helpers.cfmunge("/v2/service_bindings?q=app_guid:#{app_guid}").each do |bind|
    results << bind["entity"]["service_instance_guid"] unless user_provided_service_instance?(bind)
  end
  results
end

def write_data(orgs_results)
  stamp = Time.now.to_i
  filename = "cf-orgs-services-managers-#{stamp}.csv"
  puts "-----------\nWriting to #{filename}."

  CSV.open(filename, "wb") do |csv|
    csv << ["Name","Org ID","Managers"]
    orgs_results.each do |orgs_results|
      csv << orgs_results
    end
  end
end


# get all orgs
orgs_data = Helpers.cfmunge('/v2/organizations')
# for testing, filter out just one org
# orgs_data = Helpers.cfmunge('/v2/organizations?q=name:18f-acq')

orgs_results = Parallel.map(orgs_data, in_threads: 8) do |r|
  org_name = r["entity"]["name"]
  org = r["metadata"]["guid"]
  plans = []

  puts org_name

  # get all apps for the org
  Helpers.cfmunge("/v2/apps?q=organization_guid:#{org}").each do |app|
    boundservices = bound_services(app["metadata"]["guid"])

    # provide a total of all service instances and service plan info
    boundservices.each do |serv|
      # TODO look through all
      plan = Helpers.cfmunge("/v2/service_plans?q=service_instance_guid:#{serv}").first["entity"]["name"]
      plans.push(plan)
   end
  end

  managers = Helpers.cfmunge("/v2/organizations/#{org}/managers").map do |m|
    m["entity"]["username"]
  end

  ["#{org_name}","#{org}","#{managers.join(",")}"]
end

write_data(orgs_results)

# in its current state the script stores all bound services in "boundservices" and all service plans in "plans"
# awaiting comment on what other data we want from service plans off this comment:
# https://github.com/18F/cg-product/issues/247#issuecomment-242590177
