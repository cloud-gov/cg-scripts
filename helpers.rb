require 'json'
require 'open3'

module Helpers
  def self.cf_data(url)
    raw, _ = Open3.capture2('/usr/local/bin/cf', 'curl', url)
    # TODO handle failure
    JSON.parse(raw)
  end

  def self.cfmunge(url)
    data = self.cf_data(url)
    return data["resources"]
  end

  def self.cf_api_paginated(url)
    # https://rossta.net/blog/paginated-resources-in-ruby.html
    Enumerator.new do |y|
      loop do
        results = self.cf_data(url)
        results['resources'].each do |resource|
          y.yield resource
        end

        url = results['next_url']
        break unless url
      end
    end
  end
end
