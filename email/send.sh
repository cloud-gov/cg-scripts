#!/bin/bash
set -eo pipefail

# For each recipient email in addresses.txt, substitute the
# address into the template message and send the email
# with msmtp.
#
# For full setup instructions, see:
# https://github.com/cloud-gov/internal-docs/tree/main/docs/runbooks/Customer-Communication/email-customers.md

if [ ! -f addresses.txt ]; then
    echo "To run, create addresses.txt with one email address per line. See example-addresses.txt."
    exit 1
fi

if [ ! -f template.html ]; then
    echo "To run, create template.html with your message template. See example-template.html."
    exit 1
fi

if ! msmtp --version &> /dev/null; then
	echo "send.sh requires msmtp to be installed. See https://github.com/internal-docs/tree/main/docs/runbooks/Customer-Communication/bulk-email.md for full setup instructions."
	exit 1
fi

if [ ! -f $HOME/.msmtprc ]; then
	echo "To run, create ~/.msmtprc. See https://github.com/internal-docs/tree/main/docs/runbooks/Customer-Communication/bulk-email.md for full setup instructions."
	exit 1
fi

while read line; do
	cp template.html message.html
	# edit message.html in-place to replace the "%" placeholder with the recipient address.
	sed -e "s/%/${line}/g" -i "" message.html
	msmtp -t < ./message.html
done <addresses.txt

# clean up
rm message.html
