#!/usr/bin/env bash

set -euo pipefail
shopt -s inherit_errexit

main() {
  [[ "${BASH_VERSINFO:-0}" -ge 5 ]]     || usage "This script must be run with Bash 5.x"
  [[ $# -ge 1 && $# -le 4 ]]            || usage "Expected between 1 and 4 arguments, received $#"
  [[ -v CONCOURSE_CREDENTIALS_BUCKET ]] || usage "Expected \$CONCOURSE_CREDENTIALS_BUCKET to be set"

  FLY_TARGET=$1
  GIT_ROOT=$(git rev-parse --show-toplevel)
  PIPELINE_FILE=${2:-$GIT_ROOT/ci/pipeline.yml}
  if [[ $# -ge 3 ]]; then
    PIPELINE="$3"
  else
    PIPELINE=$(basename "$GIT_ROOT" | sed 's/^cg-//')
  fi

  TS="$(date +"%Y%m%d%H%M%S%3N")"
  SECRETS_DIR="$GIT_ROOT/do-not-commit"
  SECRETS_FILE_NAME="${4:-$(basename "$GIT_ROOT").yml}"
  SECRETS_PATH="$SECRETS_DIR/$SECRETS_FILE_NAME"
  SECRETS_BACKUP_PATH="${SECRETS_PATH}-$TS"

  ci status > /dev/null || ci login
  ci get-pipeline -p "$PIPELINE" > /dev/null 2>&1 || usage "Cannot find pipeline named $PIPELINE"

  mkdir -p "$SECRETS_DIR"
  [[ -f $SECRETS_PATH ]] && cp "$SECRETS_PATH" "$SECRETS_BACKUP_PATH"
  aws s3 cp "$CONCOURSE_CREDENTIALS_BUCKET/$SECRETS_FILE_NAME" "$SECRETS_PATH"

  ci get-pipeline -p "$PIPELINE" > "$SECRETS_DIR/pipeline-backup-$TS.yml"

  if ci validate-pipeline -c "$PIPELINE_FILE" -l "$SECRETS_PATH" > /dev/null; then
    ci set-pipeline -p "$PIPELINE" --config "$PIPELINE_FILE" -l "$SECRETS_PATH"
  fi
  echo "If you change the $SECRETS_FILE_NAME file, update the canonical creds:"
  echo
  echo "aws s3 cp --sse AES256 $SECRETS_PATH $CONCOURSE_CREDENTIALS_BUCKET/$PIPELINE.yml"
}

ci() {
  fly -t "$FLY_TARGET" "$@"
}

usage() {
  [[ $# -gt 0 ]] && (echo "  ERROR: $*"; echo)
  cat <<EOF
USAGE:

  $(basename "$0") fly-target pipeline-file [pipeline-name] [secret-file-name]

This script updates the given pipeline.  In particular, it:

1. Downloads the secrets file from S3
2. Backs up the existing pipeline definition locally
3. Validates the new pipeline file
4. Uploads the pipeline to concourse

It requires that the name of the bucket holding the secret credentials is set
in the \$CONCOURSE_CREDENTIALS_BUCKET environment variable.

If you omit pipeline-name, then the name of the root git directory is used as
a best guess (ommitting the cg- prefix).

This script assumes that "do-not-commit" is configured in the project
.gitignore (or your global excludesfile).  See the documentation on
"core.excludesfile" for more info:

  https://help.github.com/en/github/using-git/ignoring-files

Examples:

  export CONCOURSE_CREDENTIALS_BUCKET=s3://mysekrits

  $(basename "$0") concourse

  $(basename "$0") concourse ./ci/pipeline.yml

  $(basename "$0") concourse pipeline.yml deploy-foo

  $(basename "$0") concourse pipeline.yml deploy-foo deploy-foo.yml
EOF
  exit 1
}

main "$@"
