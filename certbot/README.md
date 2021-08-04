# Less-manual manual cert rotation tools

## Usage

Both scripts expect you have set the environment variable CERTBOT_BUCKET_NAME to be the name
of the bucket we use for acme-challenge files, and that you have aws authentication
available (e.g. you're running with `aws-vault exec ...`).

examples:

```bash session
$ export CERTBOT_BUCKET_NAME=our-domains-bucket
$ python3 alb_certs.py \
    --alb-listener-arn <value from prometheus> \
    --cert-name <value from prometheus>
$ export CERTBOT_BUCKET_NAME=our-cdn-bucket
$ python3 cdn_certs.py --cdn-id <value from prometheus>
```

