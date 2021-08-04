# Less-manual manual cert rotation tools

## Usage

This assumes you have set the environment variable CERTBOT_BUCKET_NAME to be the name
of the bucket we use for acme-challenge files, and that you have aws authentication
available (e.g. you're running with `aws-vault exec ...`).

