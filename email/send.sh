#!/bin/bash
set -eo pipefail

# For each recipient email in addresses.txt, substitute the
# address into the template message and send the email
# with msmtp.
#
# For full setup instructions, see:
# https://github.com/cloud-gov/internal-docs/tree/main/docs/runbooks/Customer-Communication/email-customers.md

if [ ! -f addresses.txt ]; then
    echo "To run, create addresses.txt with one email address per line. Other data can follow the email address separated by \";\". See example-addresses.txt."
    exit 1
fi

if [ ! -f template.html ]; then
    echo "To run, create template.html with your message template. See example-template.html."
    exit 1
fi

if ! msmtp --version &> /dev/null; then
	echo "send.sh requires msmtp to be installed. See https://github.com/cloud-gov/internal-docs/blob/main/docs/runbooks/Customer-Communication/email-customers.md for full setup instructions."
	exit 1
fi

if [ ! -f "$HOME/.msmtprc" ]; then
	echo "To run, create ~/.msmtprc. See https://github.com/cloud-gov/internal-docs/blob/main/docs/runbooks/Customer-Communication/email-customers.md for full setup instructions."
	exit 1
fi

while read -r line; do
  IFS=';' read -r -a array <<< "$line"

	MESSAGE="message.html"

	cp template.html "$MESSAGE"

	# edit message.html in-place to replace the "%email" placeholder with the recipient address.
	EMAIL="${array[0]}"
	sed -e "s/%email/${EMAIL}/g" -i "" "$MESSAGE"

	# this is an example of how you can replace "%space" in the template.html file with more custom data
	SPACE_NAME="${array[1]}"
	sed -e "s/%space/${SPACE_NAME}/g" -i "" "$MESSAGE"

	# this is an example of how you can replace "%org" in the template.html file with more custom data
	ORG_NAME="${array[2]}"
	sed -e "s/%org/${ORG_NAME}/g" -i "" "$MESSAGE"

	msmtp -t < "$MESSAGE"
done <addresses.txt

# clean up
rm message*.html
