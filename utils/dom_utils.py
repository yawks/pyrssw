from typing import List, Optional, Tuple, cast

from lxml import etree


def to_string(dom: etree._Element) -> str:
    return cast(str, etree.tostring(dom, method="c14n").decode("utf8"))


def get_content(dom: etree, xpaths: list) -> str:
    """get content of first found xpath in the list of xpath expressions"""
    content: str = ""
    node: Optional[etree._Element] = get_first_node(dom, xpaths)
    if node is not None:
        content = to_string(node)

    return content


def get_all_contents(dom: etree, xpaths: list, alt_to_p: bool = False) -> Tuple[str, str]:
    """Get content of all xpaths provided.

    Args:
        dom (etree): dom where to get the content
        xpaths (list): list of xpath expression used to extract content in dom object
        alt_to_p (bool, optional): If true, when an alt is found, a new element <p> is added with alt content (useful for readability). Defaults to False.

    Returns:
        str: [description]
    """
    content: str = ""
    alts: str = ""
    for xpath in xpaths:
        results = dom.xpath(xpath)
        if len(results) > 0:
            for result in results:
                enclosing: str = "%s%s"
                if result.tag != "p":
                    enclosing = "<p>%s</p>"

                alts = _get_alts(alt_to_p, result)

                content += enclosing % to_string(result)

    return content, alts


def xpath(dom: etree._Element, xpath_query: str, namespaces=None) -> List[etree._Element]:
    nodes: List[etree._Element] = []
    if dom is not None:
        if namespaces is None:
            nodes = cast(List[etree._Element], dom.xpath(xpath_query))
        else:
            nodes = cast(List[etree._Element], dom.xpath(xpath_query, namespaces=namespaces))

    return nodes


def get_attr_value(dom: etree._Element, attr_name: str) -> str:
    """Get attribute value, empty string if the attribute name does not exist.

    Args:
        dom (etree._Element): dom element
        attr_name (str): attribute name

    Returns:
        str: the attribute value if exists, "" otherwise
    """
    attr_value: str = ""

    if attr_name in dom.attrib:
        attr_value = cast(str, dom.attrib[attr_name])

    return attr_value


def text(dom: etree._Element) -> str:
    return cast(str, dom.text)

def getparent(dom: etree._Element) -> etree._Element:
    return cast(etree._Element, dom.getparent())

def _get_alts(alt_to_p: bool, result: etree._Element) -> str:
    alts: str = ""
    if alt_to_p:
        for element_with_alt in xpath(result, ".//*[@alt] | @alt/.."):
            alt: Optional[str] = get_attr_value(element_with_alt, "alt")
            if alt is not None:
                alts += alt
    return alts


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
    if node is not None:
        content = cast(str, node.text).strip()

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
