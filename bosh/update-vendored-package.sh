#!/usr/bin/env bash -ex


function usage {
  echo -e "
  ./$( basename "$0" ) -p VENDORED_PACKAGE_DIR -P VENDORED_PACKAGE -r BOSH_RELEASE_DIR -R BOSH_RELEASE_NAME [-b BOSH_DIRS_BUCKET]

  Update vendored package in bosh release. (You probably want to run this with aws-vault)
  e.g, 
  ./$( basename "$0" ) -p ./rel/or/abs/path/to/python3-boshrelease -P python3 -r /abs/or/rel/path/to/logsearch-boshrelease -R logsearch
  "
  exit
}

BOSH_DIRS_BUCKET=cloud-gov-bosh-releases

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

while getopts ":hp:P:r:R:b:" opt; do
    case "${opt}" in
        p)
            VENDORED_PACKAGE_DIR=${OPTARG}
            ;;
        P)
            VENDORED_PACKAGE_NAME=${OPTARG}
            ;;
        r)
            BOSH_RELEASE_DIR=${OPTARG}
            ;;
        R)
            BOSH_RELEASE_NAME=${OPTARG}
            ;;
        b)
            BOSH_DIRS_BUCKET=${OPTARG}
            ;;
        h | *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))


VENDORED_PACKAGE_DIR=$(realpath "${VENDORED_PACKAGE_DIR}")
pushd "${BOSH_RELEASE_DIR}" || exit


"${SCRIPT_DIR}"/get-release-artifacts.sh "${BOSH_RELEASE_NAME}" . "${BOSH_DIRS_BUCKET}"

bosh vendor-package "${VENDORED_PACKAGE_NAME}" "${VENDORED_PACKAGE_DIR}"

"${SCRIPT_DIR}"/put-release-artifacts.sh "${BOSH_RELEASE_NAME}" . "${BOSH_DIRS_BUCKET}"

popd || exit

echo "Done! Now commit and push the changes to ${BOSH_RELEASE_DIR}"
