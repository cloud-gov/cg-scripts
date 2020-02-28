#!/usr/bin/env bash

set -euo pipefail
shopt -s inherit_errexit

main() {
  [[ "${BASH_VERSINFO:-0}" -ge 5 ]]     || usage "This script must be run with Bash 5.x"
  [[ $# -ge 2 && $# -le 3 ]]            || usage "Expected two or three arguments, received $#"
  [[ -v CONCOURSE_CREDENTIALS_BUCKET ]] || usage "Expected \$CONCOURSE_CREDENTIALS_BUCKET to be set"

  FLY_TARGET=$1
  PIPELINE_FILE=$2
  if [[ -v $3 ]]; then
    PIPELINE="$3"
  else
    PIPELINE=$(basename "$GIT_ROOT")
  fi

  GIT_ROOT=$(git rev-parse --show-toplevel)
  SECRETS_DIR="$GIT_ROOT/do-not-commit"
  SECRETS_FILE="$SECRETS_DIR/$PIPELINE.yml"

  ci get-pipelines "$PIPELINE" || usage "Cannot determine pipeline name (guessed $PIPELINE)"

  mkdir "$SECRETS_DIR"
  aws s3 cp "$CONCOURSE_CREDENTIALS_BUCKET/$PIPELINE.yml" "$SECRETS_FILE"

  ci get-pipeline -p "$PIPELINE" > "$SECRETS_DIR/pipeline-backup-$(date +"%Y%m%d").yml"

  if ci validate-pipeline -c "$PIPELINE_FILE" -l "$SECRETS_FILE" > /dev/null; then
    ci set-pipeline -p "$PIPELINE" --config "$PIPELINE_FILE" -l "$SECRETS_FILE"
  fi
  echo "If you change the $SECRETS_FILE file, update the canonical creds:"
  echo
  echo "aws s3 cp --sse AES256 $SECRETS_FILE $CONCOURSE_CREDENTIALS_BUCKET/$PIPELINE.yml"
}

ci() {
  fly -t "$FLY_TARGET" "$@";
}

usage() {
  [[ $# -gt 0 ]] && echo "  ERROR: $*"
  cat <<EOF
  USAGE: $(basename "$0") fly-target pipeline-file [pipeline-name]

  This script updates the given pipeline.  In particular, it:

  1. Downloads the secrets file from S3
  2. Backs up the existing pipeline definition locally
  3. Validates the new pipeline file
  4. Uploads the pipeline to concourse

  It requires that the name of the bucket holding the secret credentials is set
  in the \$CONCOURSE_CREDENTIALS_BUCKET environment variable.

  If you omit pipeline-name, then the name of the root git directory is used as
  a best guess.

  This script assumes that "do-not-commit" is configured in the project
  .gitignore (or your global excludesfile).  See the documentation on
  "core.excludesfile" for more info:

    https://help.github.com/en/github/using-git/ignoring-files

  Examples:

    export CONCOURSE_CREDENTIALS_BUCKET=s3://mysekrits

    $(basename "$0") concourse ./ci/pipeline.yml

    $(basename "$0") concourse pipeline.yml deploy-foo
EOF
  exit 1
}

main "$@"
