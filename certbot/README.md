# Less-manual manual cert rotation tools

## all-in-one

*Note* This uses bash features not available on the default OS X bash (3.x). 
In order to run either script, make sure you've installed a newer version of
bash with homebrew

In this directory, you'll find 2 scripts for renewing all the expiring certificates
for albs and cdns: `renew_all_albs.sh` and `renew_all_cdns.sh`. These are based
heavily on the scripts used by prometheus to detect expiring certs, so the scripts
running cleanly should mean all the alerts go away, too.

Both all-in-one scripts (`renew_all_albs.sh` and `renew_all_cdns.sh`) expect
you have set the environment variable CERTBOT_BUCKET_NAME to be the name of 
the bucket we use for acme-challenge files, and that you have aws authentication
available (e.g. you're running with `aws-vault exec ...`).
`renew_all_albs.sh` further expects you to have `PREFIX` set, which is the name
prefix used in our ALB names - it should be something like `${environment}-domains-`

`renew_all_albs.sh` runs `alb_certs.py` multiple times, so it does not have any reporting
at the end about what certs failed. Because of this, you should check the entire script output 
looking for any instances that failed to rotate.

`renew_all_cdns.sh` does _not_ attempt to clean up certs. Because of this, you should run `delete-expired-server-certificates.py` after running this.

## one-at-time

Both scripts expect you have set the environment variable `CERTBOT_BUCKET_NAME` to be the name
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

