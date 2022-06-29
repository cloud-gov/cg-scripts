#!/usr/bin/env bash

GIT_USER_NAME=$(git config user.name | tr ' ' '-')

if [ -z "$GIT_USER_NAME" ]; then
    echo "Could not find user name for git. Check git config user.name"
    exit 1
fi

GIT_PGP_KEY_ID=$(git config user.signingkey)

# ensure that PGP key configured for git is for GSA email
gpg --list-keys "$GIT_PGP_KEY_ID" | grep gsa.gov
ec=$?
if [ $ec != 0 ]; then
    echo "Error: PGP key configured for git must be associated with a GSA email."
    echo "Run git config user.signingkey to see which key git is using."
    exit $ec
fi

timestamp=$(date +%s)

# delete existing PGP keys for this user
aws s3 rm s3://cg-pgp-keys --recursive --include "$GIT_USER_NAME*.asc"

# upload PGP key to S3
gpg --export --armor "$GIT_PGP_KEY_ID" | aws s3 cp --sse AES256 - "s3://cg-pgp-keys/$GIT_USER_NAME-$timestamp.asc"