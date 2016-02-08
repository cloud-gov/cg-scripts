require 'pg'
require 'json'
conn = PGconn.open(:dbname => '', :host => '', :user => '', :password=> '')
res = conn.exec('select id, settings from registry_instances')


res.each do |result|
  parsed = JSON.parse(result['settings'])
  blobstore = {"provider"=>"s3", "options"=>{"bucket_name"=>"", "credentials_source"=>"static", "access_key_id"=>"", "secret_access_key"=>"", "port"=>443, "use_ssl"=>true, "s3_force_path_style"=>false}}
  parsed['blobstore'] = blobstore
  puts "New JSON:"
  puts parsed.to_json
  before = conn.exec('select id, settings from registry_instances where id = $1', [result['id']])
  puts "Before statement:\n" + before[0]['settings'].to_s
  puts "\nRunning\n"
  conn.exec("update registry_instances set settings = $1 where id = $2", [parsed.to_json, result['id']])
  after = conn.exec('select id, settings from registry_instances where id = $1', [result['id']])
  puts "After statement:\n" + after[0]['settings'].to_s
end
