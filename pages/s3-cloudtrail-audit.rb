# to run this script: ruby s3-cloudtrail-audit.rb [filename]
require 'json'
require 'date'
filename = ARGV[0]
puts "Verifying s3 Cloudtrail log :=> #{filename}"
begin
	file = File.read(filename)

	events = JSON.parse(file)

	broker = []
	non_broker = []
	events.reverse.each do |event| #reverse to time asc order
		if ["cg-s3-broker", "cg-federalist-s3-broker"].include?(event["username"])
			next if ["PutBucketEncryption", "PutBucketPolicy", "CreateBucket", "PutBucketTagging", "DeleteBucket"].include?(event["event_name"])
			broker << event
		else
			if event["event_name"] == "PutBucketWebsite"
				next if events.select{|e| (e["bucket_name"] == event["bucket_name"]) && e["event_name"] == "CreateBucket" && (Date.parse(event["event_time"]) == Date.parse(e["event_time"]))}.first
			end
			non_broker << event
		end
	end

	report = {}
	report["log"] = events
	report["unexpected"] = (broker + non_broker).flatten
	open("./" + File.basename(filename) + DateTime.now.strftime("%Y%m%d%H%M%S"), 'w') { |f|
	  f.puts report.to_json
	}
	if broker.empty? && non_broker.empty?		
		puts "Success"
	else
		puts "Events requiring futher investigation:"
		if broker.any?
			puts "\n\nBrokered Events: #{broker.count}"
			puts broker
		end
		if non_broker.any?
			puts "\n\nNon-Brokered Events #{non_broker.count}"
			puts non_broker
		end
	end
	
rescue => ex
	puts ex
	puts ex.backtrace
end
