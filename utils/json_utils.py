from typing import  List


def get_nodes_by_name(json, node_name: str) -> List[dict]:
    """Returns a list of nodes matching the given node_name

    Arguments:
        json {dict} -- The json where to find in
        node_name {str} -- The node name to find

    Returns:
        List[dict] -- The values of nodes matching node_name
    """
    nodes: List[dict] = []
    try:
        if not json is None:
            for node in json:
                if node == node_name:
                    nodes.append(json[node])
                elif isinstance(node, list) or isinstance(node, dict):
                    nodes.extend(get_nodes_by_name(node, node_name))
                elif isinstance(json, dict) and (isinstance(json[node], dict) or isinstance(json[node], list)):
                        nodes.extend(get_nodes_by_name(json[node], node_name))
    except Exception as e:
        pass

    return nodes


def get_node_value_if_exists(node, key):
    value: str = ""
    if key in node and not node[key] is None:
        value = node[key]
    
    return value