#!/bin/bash
# set -eo pipefail

# yq operates on yaml documents using a jq-like syntax.
# For jq program syntax, see: https://stedolan.github.io/jq/manual/

if [ "$#" -ne 2 ]; then
  echo "
Usage: ./credhub-format.sh <vars-file> <deployment-name>
Example: ./credhub-format.sh vars.yml deployment > output.yml

Read from a BOSH variables file and reformat the contents to a JSON format that CredHub
can import, excluding any keys that do not appear in the manifests

Run this script from the root of the repository so it can find the manifest
file. The output file is written to stdout. Additional output, such as the keys that were
excluded, is written to stderr." >&2
  exit 1
fi

MANIFEST_PATH=${MANIFEST_PATH:-manifest.yml}

if [ ! -f "$MANIFEST_PATH" ]; then
  echo "$MANIFEST_PATH not found. Is the script being run from the root directory of the repository?" >&2
  exit 1
fi

vars_file=$1
deployment_name=$2

echo "The following values do not appear in $MANIFEST_PATH and will not be exported:
" >&2
# without setting -S, strings longer than the default of 255 will not be fully interpolated by xargs.

yq 'keys | .[]' < "$vars_file" | xargs -I % -S 512 bash -c \
"if ! grep -q % $MANIFEST_PATH; then
  echo %
fi" >&2

# reformat the credential file to the Credhub format, excluding entries
# that don't appear in pipeline.yml.
yq --output-format json < "$vars_file" | \
jq --arg deploymentname "$deployment_name" \
  --rawfile varsfile $vars_file '
  to_entries |
  map(select(.key | inside($varsfile))) |
  {
    credentials: [ .[] |
      {
        name: ("/bosh/"+$deploymentname+"/"+.key),
        type: (if .value | type == "object" then (if .value | has("certificate") then "certificate" else "json" end) else "value" end),
        value: .value
      }
    ]
  }
'
