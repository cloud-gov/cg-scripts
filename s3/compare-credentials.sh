# Pass the credential file as an arguments
main() {
    CREDENTIAL_FILE=$(basename $1)
    aws s3 cp --sse AES256 s3://concourse-credentials/$CREDENTIAL_FILE test-file-s3.yml
    diff $1 test-file-s3.yml
    rm test-file-s3.yml
    echo "do you want to upload? y/n"
    read response
    if [[ $response =  "y" ]]
    then
      aws s3 cp --sse AES256 $1 s3://concourse-credentials/$CREDENTIAL_FILE
    fi
}

main "$@"

