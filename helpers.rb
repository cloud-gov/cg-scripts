require 'json'
require 'open3'

module Helpers
  def self.cfmunge(url)
    raw, _ = Open3.capture2('/usr/local/bin/cf', 'curl', url)
    # TODO handle failure
    return cooked = JSON.parse(raw)["resources"]
  end
end
