#!/usr/bin/env ruby
# 2016 Dan Shick for 18F/GSA
# 
# cf-orgsinfo -- outputs a CSV of Cloud Foundry organizations, GUIDs,
# associated services and all org managers.
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

stamp = Time.now.to_i

CSV.open("cf-orgs-services-managers-#{stamp}.csv", "wb") do |csv|
  csv << ["Name","Org ID","Managers"]
end

#cfmunge('/v2/organizations?q=name:18f-acq').each do |r|
# for testing, filter out just one org

# loop 1: get all orgs
cfmunge('/v2/organizations?q=name:18f-acq').each do |r|
  name = r["entity"]["name"]
  org = r["metadata"]["guid"]
  boundservicesall = Array.new
  plans = Array.new

# loop 2: get all apps for the org
  cfmunge("/v2/apps?q=organization_guid:#{org}").each do |app|

# loop 3: for each app, get its service bindings and use them to create a list of bound services
# not user-provided
    cfmunge("/v2/service_bindings?q=app_guid:#{app["metadata"]["guid"]}").each do |bind|
      boundservicesall.push(bind["entity"]["service_instance_guid"]) unless bind["entity"]["service_instance_url"].match('user_provided_service_instances')

    end

# after that we will provide a total of all service instances
# and service plan info

    boundservices = boundservicesall.uniq
    boundservices.each do |serv|
      plans.push(cfmunge("/v2/service_plans?q=service_instance_guid:#{serv}").first["entity"]["name"])
   end
  end
  managers = Array.new
  cfmunge("/v2/organizations/#{org}/managers").each do |m|
    managers.push(m["entity"]["username"])
  end
  CSV.open("cf-orgs-services-managers-#{stamp}.csv", "ab") do |csv|
    csv << ["#{name}","#{org}","#{managers.join(",")}"]
  end
end

# in its current state the script stores all bound services in "boundservices" and all service plans in "plans"
# awaiting comment on what other data we want from service plans off this comment:
# https://github.com/18F/cg-product/issues/247#issuecomment-242590177
