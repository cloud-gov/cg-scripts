# Pass the credential file as an argument
main() {
    CREDENTIAL_FILE=$(basename $1)
    tmpfile=$(mktemp)
    aws s3 cp --sse AES256 s3://concourse-credentials/$CREDENTIAL_FILE "$tmpfile"
    mv "$tmpfile" $CREDENTIAL_FILE
}

main "$@"
