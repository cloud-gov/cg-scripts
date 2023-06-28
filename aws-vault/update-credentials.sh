main() {
    CREDENTIAL_FILE=$(basename $1)
    aws-vault exec gov-prd-plat-admin -- aws s3 cp --sse AES256 s3://concourse-credentials/$CREDENTIAL_FILE "2${CREDENTIAL_FILE}"
    rm $1
    mv "2${CREDENTIAL_FILE}" $CREDENTIAL_FILE
}

main "$@"
