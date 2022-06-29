#!/usr/bin/env bash

PGP_KEYS_BUCKET="cg-pgp-keys"
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

PGP_TMP_FILE=$(mktemp)
gpg --export --armor "$GIT_PGP_KEY_ID" > "$PGP_TMP_FILE"

# upload PGP key to S3
aws s3 cp --sse AES256 "$PGP_TMP_FILE" "s3://$PGP_KEYS_BUCKET/$GIT_USER_NAME.asc" || true

rm "$PGP_TMP_FILE"