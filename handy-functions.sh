function paginate_v3_api_for_parameter {
    # get all of a specific parameter for a v3 api call
    # ex. 
    # paginate_v3_api_for_parameter /v3/spaces?organization_guids=foo guid
    # would return the guid of all spaces with organization guid foo
    next_page=$1
    parameter=$2
    # trailing space is important to keep the last item of the list from joining from the first next time around
    while [[ -n ${next_page} ]]; do
        response=$(cf curl ${next_page}) 
        echo ${response} | jq -r .resources\[\].${parameter}
        next_page=$(get_next_page "${response}")
    done
}
function get_next_page {
    # get the next page from a json response
    echo $1 | jq -r '.pagination.next' | sed -n -e 's_^.*/v3_/v3_p' 
}
