import subprocess
import unittest
from unittest.mock import patch
import json
import asg_tool


def result_resource(
    guid=None,
    created_at=None,
    updated_at=None,
    name=None,
    relationships=None,
    metadata=None,
    links=None,
) -> dict:
    return {
        "guid": guid,
        "created_at": created_at,
        "updated_at": updated_at,
        "name": name,
        "relationships": relationships,
        "metadata": metadata,
        "links": links,
    }


def result_pagination(
    total_results=None,
    total_pages=None,
    first=None,
    last=None,
    next=None,
    previous=None,
) -> dict:
    return {
        "total_results": total_results,
        "total_pages": total_pages,
        "first": first,
        "last": last,
        "next": next,
        "previous": previous,
    }


def results_from_cf(
    pagination=result_pagination(), resources=[result_resource()]
) -> dict:
    return {"pagination": pagination, "resources": resources}


class SubprocessResult:
    def __init__(self, stdout={}, stderr={}):
        self.stdout = json.dumps(stdout)
        self.stderr = json.dumps(stderr)


def create_resource(guid, name):
    resource = result_resource(guid=guid, name=name)
    return resource


def return_cf_request(
    pagination=result_pagination(),
    resource=result_resource(),
    number_or_resources=1,
    resources=None,
):
    if not resources:
        resources = list(resource for i in range(0, number_or_resources))

    stdout = results_from_cf(pagination=pagination, resources=resources)
    output = SubprocessResult(stdout=stdout)

    return output


class TestASGGetSpaces(unittest.TestCase):
    @patch("subprocess.run")
    def test_paginate_response_one_page(self, mock_call):
        expected_keys = ["guid", "name"]
        mock_call.return_value = return_cf_request(
            resource=create_resource("a-guid-id", "a-name"), number_or_resources=10
        )
        result = asg_tool.get_spaces()
        self.assertIsInstance(result, list)
        self.assertEqual(list(result[0].keys()), expected_keys)
        self.assertEqual(len(result), 10)

    @patch("subprocess.run")
    def test_paginate_max_100_calls(self, mock_call):
        pagination = result_pagination(
            next={"href": "http://example.gov/items?per_page=10"}
        )
        mock_call.return_value = return_cf_request(
            resource=create_resource("a-guid-id", "a-name"), pagination=pagination
        )
        result = asg_tool.get_spaces()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 100)

    def test_paginate_response_two_pages(self):
        pagination_1 = result_pagination(
            next={"href": "http://example.gov/items?per_page=10"}
        )
        mock_call_1 = return_cf_request(
            resource=create_resource("a-guid-id", "a-name"),
            pagination=pagination_1,
            number_or_resources=10,
        )
        mock_call_2 = return_cf_request(
            resource=create_resource("other-guid-id", "other-name"),
            number_or_resources=5,
        )

        with patch("subprocess.run", side_effect=[mock_call_1, mock_call_2]):
            expected_keys = ["guid", "name"]
            result = asg_tool.get_spaces()
            self.assertIsInstance(result, list)
            self.assertEqual(list(result[0].keys()), expected_keys)
            self.assertEqual(len(result), 15)

    @patch("subprocess.run")
    def test_remove_invalid_resources_from_list(self, mock_call):
        expected_keys = ["guid", "name"]
        valid_resources = list(
            create_resource("a-guid", "a-name") for i in range(0, 10)
        )
        invalid_resources = list(create_resource(None, None) for i in range(0, 10))
        all_resources = valid_resources + invalid_resources
        self.assertEqual(len(all_resources), 20)
        mock_call.return_value = return_cf_request(resources=all_resources)
        result = asg_tool.get_spaces()
        self.assertIsInstance(result, list)
        self.assertEqual(list(result[0].keys()), expected_keys)
        self.assertEqual(len(result), 10)


class TestCheckSpaceASG(unittest.TestCase):
    def test_curl_space_asg(self):
        pass


class TestGetSpaceASG(unittest.TestCase):
    @patch("subprocess.run")
    def test_gets_asg_guid(self, mock_call):
        asg_name = "asg-name"
        asg_guid = "asg-guid-id"
        mock_call.return_value = return_cf_request(
            resource=create_resource(asg_guid, asg_name)
        )
        result = asg_tool.get_asg_guid(asg_name)
        self.assertIsInstance(result, str)
        self.assertEqual(result, asg_guid)

    @patch("subprocess.run")
    def test_gets_none_when_asg_name_not_found(self, mock_call):
        asg_name = "asg-name"
        other_asg_name = "other-asg-name"
        other_asg_guid = "other-asg-guid-id"
        mock_call.return_value = return_cf_request(
            resource=create_resource(other_asg_guid, other_asg_name)
        )
        result = asg_tool.get_asg_guid(asg_name)
        self.assertEqual(result, None)


if __name__ == "__main__":
    unittest.main()
