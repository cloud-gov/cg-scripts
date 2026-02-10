#!/bin/bash
set -eo pipefail

# yq operates on yaml documents using a jq-like syntax.
# For jq program syntax, see: https://stedolan.github.io/jq/manual/

if [ "$#" -ne 2 ]; then
  echo "
Usage: ./credhub-format.sh <vars-file> <credhub-prefix>
Example: ./credhub-format.sh vars.yml /bosh/deployment > output.json

You can optionally override the location for your manifest, which
defaults to manifest.yml:

MANIFEST_PATH=deploy/manifest.yml ./credhub-format.sh credentials.yml deploy-something > output.yml

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

VARS_FILE=$1
CREDHUB_VAR_PREFIX=$2

echo "The following values do not appear in $MANIFEST_PATH and will not be exported:
" >&2
# without setting -S, strings longer than the default of 255 will not be fully interpolated by xargs.

yq 'keys | .[]' < "$VARS_FILE" | xargs -I % -S 512 bash -c \
"if ! grep -q % $MANIFEST_PATH; then
  echo %
fi" >&2

MANIFEST_VARS=$(cat "$MANIFEST_PATH" | yq '.variables' --output-format json | jq 'map({(.name): .}) | add')

# reformat the credential file to the Credhub format, excluding entries
# that don't appear in the manifest
yq --output-format json < "$VARS_FILE" | \
jq --arg credhub_var_prefix "$CREDHUB_VAR_PREFIX" \
  --argjson manifest_vars "$MANIFEST_VARS" \
  --rawfile varsfile "$VARS_FILE" '
  to_entries |
  map(select(.key | inside($varsfile))) |
  {
    credentials: [ .[] |
      {
        name: ($credhub_var_prefix+"/"+.key),
        type: ($manifest_vars[.key].type // if .value | type == "object" then "json" else "value" end),
        value: .value
      }
    ]
  }
'
