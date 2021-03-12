from typing import List, Optional, Union


def get_nodes_by_name(json, node_name: str) -> List[dict]:
    """Returns a list of nodes matching the given node_name

    Arguments:
        json {dict} -- The json where to find in
        node_name {str} -- The node name to find

    Returns:
        List[dict] -- The values of nodes matching node_name
    """
    nodes: List[dict] = []
    if json is not None:
        for node in json:
            if node == node_name:
                if isinstance(json, list):
                    node = json
                else:
                    nodes.append(json[node])
            elif isinstance(node, (list, dict)):
                nodes.extend(get_nodes_by_name(node, node_name))
            elif isinstance(json, dict) and isinstance(json[node], (dict, list)):
                nodes.extend(get_nodes_by_name(json[node], node_name))

    return nodes


def get_node(json: dict, *kwargs):
    """equivalent to xpath. Return the node following kwargs node names

    Args:
        json (dict): root

    Returns:
        Union[Optional[dict], str]: value or json node
    """
    node = None
    found: bool = True
    if kwargs is not None and len(kwargs) > 0:
        node = json
        for node_name in kwargs:
            if node is not None and (isinstance(node_name, int) or node_name in node):
                node = node[node_name]
            else:
                found = False
                break

    return node if found else None


def get_node_value_if_exists(node, key) -> str:
    value: str = ""
    if key in node and not node[key] is None:
        value = node[key]

    return value
