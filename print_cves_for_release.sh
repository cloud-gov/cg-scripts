#!/bin/bash

set -e

if [ "$#" -ne 1 ]; then
    echo "./print_cves_for_release.sh RELEASE_VERSION"
    echo "Example: ./print_cves_for_release.sh v248"
    exit 1
fi

RELEASE=$1

URLs=$(curl -s "https://github.com/cloudfoundry/cf-release/releases/tag/${RELEASE}" | grep -o '"http.*USN.*/"' | tr -d '"')

for URL in $URLs
do
    USN=$(curl -s $URL)

    tmpfile=$(mktemp /tmp/security.XXXXXX)
    $(echo "$USN" > $tmpfile)

    printf "%s" "- [$(grep -o '<h1>.*</h1>' $tmpfile | sed -e 's/<[^>]*>//g')]($URL). "
    
    CVEs=$(sed -n -e '/References/,$p' $tmpfile | grep -o "<a.*CVE.*/a>")
    CVEs=$(echo "$CVEs" | sed 's/<a href="//g; s/">/        /g; s/<\/a>,*//g' | awk '{print "["$2"]("$1")"}')
    rm $tmpfile

    CVEArray=()
    for CVE in $CVEs
    do
        CVEArray+=("$CVE")
    done
    if [ ${#CVEArray[@]} -lt 2 ]; then
        printf "%s\n" "The associated CVE is $CVEs."
    else
        CVEString=$(printf ", %s" "${CVEArray[@]}")
        CVEString=${CVEString:2}
        printf "%s\n" "The associated CVEs are $CVEString."
    fi
done
