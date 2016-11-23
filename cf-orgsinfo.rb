#!/usr/bin/env ruby
# 2016 Dan Shick for 18F/GSA
#
# cf-orgsinfo -- outputs a CSV of Cloud Foundry organizations, GUIDs,
# associated services and all org managers.
# You must be authenticated to a CF API for this to work, as it uses
# "cf curl".

require 'csv'
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


stamp = Time.now.to_i
filename = "cf-orgs-services-managers-#{stamp}.csv"
puts "Writing to #{filename}.\n-----------"

CSV.open(filename, "wb") do |csv|
  csv << ["Name","Org ID","Managers"]

  #Helpers.cfmunge('/v2/organizations?q=name:18f-acq').each do |r|
  # for testing, filter out just one org

  # get all orgs
  Helpers.cfmunge('/v2/organizations').each do |r|
    org_name = r["entity"]["name"]
    org = r["metadata"]["guid"]
    plans = []

    puts org_name

    # get all apps for the org
    Helpers.cfmunge("/v2/apps?q=organization_guid:#{org}").each do |app|
      app_name = app['entity']['name']
      puts "  #{app_name}"

      boundservices = bound_services(app["metadata"]["guid"])

      # provide a total of all service instances and service plan info
      boundservices.each do |serv|
        # TODO look through all
        plan = Helpers.cfmunge("/v2/service_plans?q=service_instance_guid:#{serv}").first["entity"]["name"]
        plans.push(plan)
     end
    end

    managers = []
    Helpers.cfmunge("/v2/organizations/#{org}/managers").each do |m|
      managers.push(m["entity"]["username"])
    end

    csv << ["#{org_name}","#{org}","#{managers.join(",")}"]
  end
end

# in its current state the script stores all bound services in "boundservices" and all service plans in "plans"
# awaiting comment on what other data we want from service plans off this comment:
# https://github.com/18F/cg-product/issues/247#issuecomment-242590177
