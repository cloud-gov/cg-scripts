#!/bin/bash -ex
# User input or guess keyword
if [[ -z $1 ]]
    then
        KEY=$(pwd | awk -F/ '{print $NF}')
    else
        KEY="$1"
fi
# verify the pipeline name looks good
PIPELINE=$(fly -t fr pipelines | grep "${KEY}" | awk '{print $1}')
echo "Pipeline selected:" "${PIPELINE}"

# Do the next block
CFG=$(aws s3 ls s3://concourse-credentials | grep "${KEY}" | awk '{print $4}')
echo "Found config file:" "${CFG}"
aws s3 cp "s3://concourse-credentials/${CFG}" .

# Save for later just in case
BACKUP="$(date +"%Y%m%d")_${PIPELINE}.yml"
fly -t fr gp -p "${PIPELINE}" > "${BACKUP}"
fly validate-pipeline -c pipeline.yml -l "${CFG}"
# Make sure it says "looks good"

echo "If the above command says 'looks good', review and reconcile changes:"
echo "fly -t fr sp -p ${PIPELINE} --config pipeline.yml -l ${CFG}"

echo "IF you changed the config file, update the canonical creds:"
echo "aws s3 cp --sse AES256 ${CFG} s3://concourse-credentials/${CFG}"

echo "Original pipeline saved to ${BACKUP} - DO NOT COMMIT THIS FILE"