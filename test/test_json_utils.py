
from utils.json_utils import get_nodes_by_name


def test_get_nodes_by_name():
    _json = {
        "tree": {
            "children": [
                {
                    "child1": {
                        "article": "this is my 1st article"
                    },
                    "child2": {
                        "article": {
                            "title": "this is my 2nd article",
                            "content": "this is the content of the 2nd article"
                        },
                        "otherentry": "with any value"
                    },
                },
                {
                    "key": "value"
                }
            ],
            "summary": {
                "children": {
                    "article": "another article"
                },
                "other_entry": "value"
            }
        }
    }

    nodes = get_nodes_by_name(_json, "article")

    if len(nodes) != 3:
        raise AssertionError
    if nodes[0] != "this is my 1st article":
        raise AssertionError
    if nodes[2] != "another article":
        raise AssertionError
    if not isinstance(nodes[1], dict):
        raise AssertionError
    if "title" not in nodes[1]:
        raise AssertionError
    if nodes[1]["title"] != "this is my 2nd article":
        raise AssertionError
