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

def cfmunge(url)
  raw = %x(/usr/local/bin/cf curl "#{url}")
  return cooked = JSON.parse(raw)["resources"]
end

stamp = Time.now.to_i

CSV.open("cf-orgs-services-managers-#{stamp}.csv", "wb") do |csv|
  csv << ["Name","Org ID","Services","Managers"]
end

cfmunge('/v2/organizations').each do |r|
  name = r["entity"]["name"]
  org = r["metadata"]["guid"]
  services = Array.new
  cfmunge("/v2/organizations/#{org}/services").each do |s|
    services.push(s["entity"]["label"])
  end   
  managers = Array.new
  cfmunge("/v2/organizations/#{org}/managers").each do |m|
    managers.push(m["entity"]["username"])
  end
  CSV.open("cf-orgs-services-managers-#{stamp}.csv", "ab") do |csv|
    csv << ["#{name}","#{org}","#{services.join(",")}","#{managers.join(",")}"]
  end
end
