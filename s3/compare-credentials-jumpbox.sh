# Pass the credential file as an argument
main() {
    CREDENTIAL_FILE=$(basename $1)
    tmp_file=$(mktemp)
    aws s3 cp --sse AES256 s3://concourse-credentials/$CREDENTIAL_FILE $tmp_file
    diff $1 $tmp_file
    rm $tmp_file
    echo "do you want to upload? y/n"
    read response
    if [[ $response = "y" ]]
    then
      aws s3 cp --sse AES256 $1 s3://concourse-credentials/$CREDENTIAL_FILE
    fi
}

main "$@"

