# This script uses the cf cli to do the most basic provisioning of
# a new Cloud Foundry deployment user for an org.
#
# Usage:
#   $ ./cf-create-deployer-user.sh <org>
#
set -e
if [ -z $1 ]; then
  echo
  echo "Usage:"
  echo "    $ ./cf-create-deployer-user.sh <org>"
  echo
  exit 1;
fi

USER_ORG=$1
USER_NAME=${USER_ORG}_deployer

# Generate a password.
USER_PASS=`./generate-passphrase`

# What we expect to see back from the CLI.
RETURN_PASS='OK'
RETURN_FAIL='FAILED'
RETURN_EXISTS='already exists'

echo "Creating user:" $USER_NAME
RETURN_CREATE=`cf create-user $USER_NAME $USER_PASS`
if [[ $RETURN_CREATE =~ $RETURN_EXISTS ]]
then
  echo "User already exists"
elif [[ $RETURN_CREATE =~ $RETURN_PASS ]]
then
  echo "Success!"
  echo "New User:" $USER_NAME
  echo "Create a fugacious.18f.gov message with pass:" $USER_PASS
  ### TODO: create fugacious link automatically. Something up with 18f version.
  # PASS_LINK=`./fugu -t 12 -v 2 $USER_PASS`
  # echo "Password Link:" $PASS_LINK

else
  echo "Something's wrong" + $RETURN_CREATE
fi


# Make the user an OrgAuditor.
cf set-org-role $USER_NAME $USER_ORG OrgAuditor

# Set permissions as SpaceDeveloper for each space so the user can
# deploy apps
cf target -o $USER_ORG
cf spaces \
| awk 'm;/^name/{m=1}' \
| while read SPACE_NAME
    do cf set-space-role $USER_NAME $USER_ORG $SPACE_NAME SpaceDeveloper
  done

echo "done."

