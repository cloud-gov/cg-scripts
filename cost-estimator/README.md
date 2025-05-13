# Estimate Costs

## Quick Start

```shell
python3 -m venv .venv
pip3 install -r requirements.txt
aws-vault exec gov-prd-plat-admin -- bash
source .venv/bin/activate
cf login --sso
./estimate-costs.py sandbox-pif
```

## Troubleshooting

If you get the errors

```text
  File "/Users/peterdburkholder/Projects/cloud-gov/estimate-costs/venv/lib/python3.13/site-packages/botocore/httpsession.py", line 493, in send
    raise EndpointConnectionError(endpoint_url=request.url, error=e)
botocore.exceptions.EndpointConnectionError: Could not connect to the endpoint URL: "https://tagging-fips.us-gov-west-1.amazonaws.com/"
```

Then update your `~/.aws/config` to comment out the line:

```text
# ========= 2025-05-07 ==========
#[default]
#use_fips_endpoint=true
```

