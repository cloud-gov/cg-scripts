#!/bin/bash
set -eo pipefail

# yq operates on yaml documents using a jq-like syntax.
# For jq program syntax, see: https://stedolan.github.io/jq/manual/

if [ "$#" -ne 2 ]; then
  echo "
Usage: ./credhub-format.sh <source-file> <pipeline-name>
Example: ./credhub-format.sh credentials.yml deploy-something > output.yml

You can optionally override the location for your pipeline configuration, which
defaults to ci/pipeline.yml:

PIPELINE_CONFIG_PATH=pipeline.yml ./credhub-format.sh credentials.yml deploy-something > output.yml

Read from a credential file and reformat the contents to a JSON format that CredHub
can import, excluding any keys that do not appear in the pipeline configuration file.

Run this script from the root of the repository so it can find the pipeline configuration
file. The output file is written to stdout. Additional output, such as the keys that were
excluded, is written to stderr." >&2
  exit 1
fi

# check silently if yq is installed.
if ! which -s yq; then
  echo "yq is required to run this script." >&2
  exit 1
fi

PIPELINE_CONFIG_PATH=${PIPELINE_CONFIG_PATH:-ci/pipeline.yml}

if [ ! -f "$PIPELINE_CONFIG_PATH" ]; then
  echo "$PIPELINE_CONFIG_PATH not found. Is the script being run from the root directory of the repository?" >&2
  exit 1
fi

source=$1
pipelinename=$2

echo "The following values do not appear in $PIPELINE_CONFIG_PATH and will not be exported:
" >&2
# without setting -S, strings longer than the default of 255 will not be fully interpolated by xargs.
yq 'keys | .[]' < "$source" | xargs -I % -S 512 bash -c \
"if ! grep -q % $PIPELINE_CONFIG_PATH; then
  echo %
fi" >&2

# reformat the credential file to the Credhub format, excluding entries
# that don't appear in pipeline.yml.
yq --output-format json < "$source" | \
jq --arg pipelinename $pipelinename \
  --rawfile pipeline $PIPELINE_CONFIG_PATH '
  to_entries |
  map(select(.key | inside($pipeline))) |
  {
    credentials: [ .[] |
      {
        name: ("/concourse/main/"+$pipelinename+"/"+.key),
        type: (if .value | type == "object" then "json" else "value" end),
        value: .value
      }
    ]
  }
'

# after connecting to jumpbox:
# cat << EOF > import.yml
# <paste here>
# EOF
