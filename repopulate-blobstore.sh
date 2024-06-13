RELEASES=$(bosh releases --json)
for row in $(echo "${RELEASES}" | jq -r '.Tables[0].Rows[] | @base64'); do
    _jq() {
      echo ${row} | base64 --decode | jq -r ${1}
    }
    NAME=$(_jq '.name')
    VERSION=$(_jq '.version')
    echo "${NAME}","${VERSION}"
done

