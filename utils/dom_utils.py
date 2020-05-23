from typing import List, Optional

from lxml import etree


def get_content(dom: etree, xpaths: list) -> str:
    """get content of first found xpath in the list of xpath expressions"""
    content: str = ""
    node: Optional[etree._Element] = get_first_node(dom, xpaths)
    if not node is None:
        content = etree.tostring(node, encoding='unicode')

    return content

def get_text(dom: etree, xpaths: list) -> str:
    """get text of first node found in first matching xpath in the list

    Arguments:
        dom {etree} -- dom
        xpaths {list} -- list of xpath expressions

    Returns:
        str -- text of the first node in the first matching xpath expression
    """
    content: str = ""
    node: Optional[etree._Element] = get_first_node(dom, xpaths)
    if not node is None:
        content = node.text.strip()
    
    return content

def get_first_node(dom: etree, xpaths: list) -> Optional[etree._Element]:
    """get first node found in the list of xpath expressions"""
    node: Optional[etree._Element] = None
    for xpath in xpaths:
        results = dom.xpath(xpath)
        if len(results) > 0:
            node = results[0]
            break
    return node

def delete_xpaths(dom: etree, xpaths: List[str]):
    """delete nodes of the given dom matching xpath exrepssions"""
    for xpath in xpaths:
        delete_nodes(dom.xpath(xpath))

def delete_nodes(nodes):
    """delete list of nodes"""
    for node in list(nodes):
        node.getparent().remove(node)

def get_xpath_expression_for_filters(parameters, xpath_to_include, xpath_to_exclude):
    """Get xpath expression to filter item depending on parameters and xpath expressions passed xpath_to_include and xpath_to_exclude must contain ## to be replaced by category text
    """
    # filter only on passed category
    others_than_listed = False
    if parameters["filter"][:1] == "^":  # other categories than listed
        # in case of many categories given, separated by comas
        categories = parameters["filter"][1:].split(",")
        others_than_listed = True
    else:
        # in case of many categories given, separated by comas
        categories = parameters["filter"].split(",")

    # build xpath expression
    xpath_expression = ""
    for category in categories:
        if others_than_listed:
            if len(xpath_expression) > 0:
                xpath_expression += " or "
            xpath_expression += xpath_to_include % category
        else:
            if len(xpath_expression) > 0:
                xpath_expression += " and "
            xpath_expression += xpath_to_exclude % category
    return "//rss/channel/item[%s]" % xpath_expression
