
get_bucket_size() {
 bucket_name=$1
 total_size=$(aws cloudwatch get-metric-statistics \
 --namespace AWS/S3 \
 --metric-name BucketSizeBytes \
 --dimensions Name=BucketName,Value="$bucket_name" Name=StorageType,Value=StandardStorage \
 --start-time $(date -u -v-1d +%Y-%m-%dT%H:%M:%SZ) \
 --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
 --period 86400 \
 --statistics Average \
 --query "Datapoints[0].Average" \
 --output text)

 if [[ "$total_size" == "None" ]]; then
    echo "empty"
 else
    echo "$total_size bytes"
 fi
}

get_bucket_tags() {
    bucket_name=$1
    tags=$(aws s3api get-bucket-tagging --bucket "$bucket_name" --query "TagSet" --output json 2>/dev/null)
    if [[ "$tags" == "[]" ]]; then
      echo "No Tags"
    else
      echo "$tags" | jq -r  'map("\(.Key)=\(.Value)") | join(", ")'
    fi
}

convert_size_to_human_readable() {
 size=$1
 if [ "$size" -lt 1024 ]; then
    echo "${size} Bytes"
 elif [ "$size" -lt $((1024**2)) ]; then
    echo "$(($size / 1024)) KB"
 elif [ "$size" -lt $((1024*3)) ]; then
    echo "$(($size / 1024**2)) MB"
 elif [ "$size" -lt $((1024**4)) ]; then
    echo "$(($size / 1024**3)) GB"
 else
    echo "$(($size / 1024**4)) TB"
 fi
}

buckets=$(aws s3api list-buckets --query "Buckets[].Name" --output json | jq -r '.[]' | grep -E '^cg-')

echo -e "Bucket Name\tSize\tTags" >> s3buckets.txt

for bucket in $buckets; do
    bucket_size=$(get_bucket_size "$bucket")

    bucket_tags=$(get_bucket_tags "$bucket")
    echo -e "$bucket\t$bucket_size\t$bucket_tags" >> s3buckets.txt
done