#!/bin/bash

set -x

for ID in $(aws cloudfront list-distributions | jq -r '.DistributionList.Items[].Id'); do
  TEMPDIR=$(mktemp -d)
  CONFIG=$(aws cloudfront get-distribution-config --id ${ID})
  ETAG=$(echo "${CONFIG}" | jq -r '.ETag')
  VERSION=$(echo "${CONFIG}" | jq -r '.DistributionConfig.ViewerCertificate.MinimumProtocolVersion')

  if [ "${VERSION}" == "TLSv1" ]; then
    echo "Updating ${ID} with ETAG ${ETAG} from ${VERSION} to TLSv1_2016"
    echo "${CONFIG}" | jq '.DistributionConfig' > ${TEMPDIR}/orig.json
    echo "${CONFIG}" | jq '.DistributionConfig | .ViewerCertificate.MinimumProtocolVersion = "TLSv1_2016"' > ${TEMPDIR}/updated.json
    aws cloudfront update-distribution --id ${ID} --distribution-config file://${TEMPDIR}/updated.json --if-match "${ETAG}"
    aws cloudfront get-distribution-config --id ${ID} | jq '.DistributionConfig' > ${TEMPDIR}/updated-tlsv1_2016.json
    diff -u ${TEMPDIR}/orig.json ${TEMPDIR}/updated-tlsv1_2016.json
  fi

  rm -rf ${TEMPDIR}
done
