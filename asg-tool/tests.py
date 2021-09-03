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


def return_cf_request(
    pagination=result_pagination(), resource=result_resource(), number_or_resources=1
):
    resources = list(resource for i in range(0, number_or_resources))

    stdout = results_from_cf(pagination=pagination, resources=resources)
    output = SubprocessResult(stdout=stdout)

    return output


class TestASGTool(unittest.TestCase):
    @patch("subprocess.run")
    def test_paginate_response_one_page(self, mock_call):
        mock_call.return_value = return_cf_request(number_or_resources=10)
        expected_keys = result_resource().keys()
        result = asg_tool.get_spaces()
        self.assertIsInstance(result, list)
        self.assertEqual(result[0].keys(), expected_keys)
        self.assertEqual(len(result), 10)

    @patch("subprocess.run")
    def test_paginate_max_100_calls(self, mock_call):
        pagination = result_pagination(
            next={"href": "http://example.gov/items?per_page=10"}
        )
        mock_call.return_value = return_cf_request(pagination=pagination)
        result = asg_tool.get_spaces()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 100)

    def test_paginate_response_two_pages(self):
        pagination_1 = result_pagination(
            next={"href": "http://example.gov/items?per_page=10"}
        )
        mock_call_1 = return_cf_request(pagination=pagination_1, number_or_resources=10)
        mock_call_2 = return_cf_request(number_or_resources=5)

        with patch("subprocess.run", side_effect=[mock_call_1, mock_call_2]):
            expected_keys = result_resource().keys()
            result = asg_tool.get_spaces()
            self.assertIsInstance(result, list)
            self.assertEqual(result[0].keys(), expected_keys)
            self.assertEqual(len(result), 15)


if __name__ == "__main__":
    unittest.main()
