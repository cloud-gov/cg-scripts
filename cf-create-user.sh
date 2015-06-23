# This script uses the cf cli to do the most basic provisioning of
# a new Cloud Foundry user. Usage:
#
#   $ ./cf-create-user.sh <username> [<org>]
#
# Include the <org> to create a new organization and make the user an OrgManager.
set -e

USER_EMAIL=$1

# Strip the host portion of the email supplied.
USER_NAME="${USER_EMAIL%%@*}"
USER_ORG=$2

# Generate a password.
USER_PASS=`openssl rand -base64 15`

# What we expect to see back from the CLI.
RETURN_PASS='OK'
RETURN_FAIL='FAILED'
RETURN_EXISTS='already exists'

FUGU_URL='https://raw.githubusercontent.com/jgrevich/fugacious/feature/14_fugacious-CLI/bin/fugu'

# Should this go somewhere else? Doesn't seem like a terrible
# place for now.
FUGU_PATH="${HOME}/.cf/bin"
if [[ ! -d ${FUGU_PATH} ]]
  then
    echo "Creating:" $FUGU_PATH
    mkdir -p $FUGU_PATH
  else
    echo "Fugu path exists."
fi

# Grab fugu for password handling.
if [[ ! -f ${FUGU_PATH}/fugu ]]
  then
    curl -s -o ${FUGU_PATH}/fugu $FUGU_URL
    chmod +x ${FUGU_PATH}/fugu
  else
    echo "Found fugu at:" ${FUGU_PATH}/fugu
fi

# Can't get users with cf and don't want to worry about having
# current uaac auth so just and try and create.
echo "Creating user:" $USER_EMAIL
RETURN_CREATE=`cf create-user $USER_EMAIL $USER_PASS`
if [[ $RETURN_CREATE =~ $RETURN_EXISTS ]]
then
  echo "User already exists"
elif [[ $RETURN_CREATE =~ $RETURN_PASS ]]
then
  echo "Creating fugacious link with pass:" $USER_PASS
  PASS_LINK=`$FUGU_PATH/fugu $USER_PASS`
  echo "Success!"
  echo "New User:" $USER_EMAIL
  echo "Password Link:" $PASS_LINK
else
  echo "Something's wrong" + $RETURN_CREATE
fi

# Target the sandbox org.
RETURN_TARGET=`cf target -o sandbox`
if [[ $RETURN_TARGET =~ $RETURN_FAIL ]]
then
  echo "Something went wrong!"
  echo $RETURN_TARGET
fi

# If the org doesn't exist, create it.
echo "Creating personal space:" $USER_NAME
if [[ ! `cf spaces` =~ $USER_NAME ]]
then
  cf create-space $USER_NAME
else
  echo "Space already exists."
fi

# Set user permissions.
cf set-space-role $USER_EMAIL sandbox $USER_NAME SpaceDeveloper
cf set-space-role $USER_EMAIL sandbox $USER_NAME SpaceManager

# Create the org if supplied and give the user perms.
if [[ ! $USER_ORG == '' ]]
then
  # If the org doesn't exist, create it.
	echo "Creating org:" $USER_ORG
	if [[ ! `cf orgs` =~ $USER_ORG ]]
	then
	  cf create-org $USER_ORG
	else
	  echo "Org already exists."
	fi

  # Make the user a manager.
  cf set-org-role $USER_EMAIL $USER_ORG OrgManager

  # Since the typical expectation is that being OrgManager confers
  # access to the contained spaces as well, but doesn't we'll go
  # ahead and add those permissions.
  cf target -o $USER_ORG
  cf spaces \
  | awk 'm;/^name/{m=1}' \
  | while read SPACE_NAME
      do cf set-space-role $USER_EMAIL $USER_ORG $SPACE_NAME SpaceDeveloper
         cf set-space-role $USER_EMAIL $USER_ORG $SPACE_NAME SpaceManager
    done
fi
