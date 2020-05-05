import lxml.etree
from typing import List

def getContent(dom: lxml.etree, xpaths: list) -> str:
    """get content of first found xpath in the list of xpath expressions"""
    content = ""
    for xpath in xpaths:
        results = dom.xpath(xpath)
        if len(results) > 0:
            content = lxml.etree.tostring(results[0], encoding='unicode')
            break

    return content

def deleteXPaths(dom: lxml.etree, xpaths: List[str]):
    """delete nodes of the given dom matching xpath exrepssions"""
    for xpath in xpaths:
        deleteNodes(dom.xpath(xpath))

def deleteNodes(nodes):
    """delete list of nodes"""
    for node in list(nodes):
        node.getparent().remove(node)

def getXpathExpressionForFilters(parameters, xpath_to_include, xpath_to_exclude):
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
            xpath_expression += xpath_to_exclude % category
        else:
            if len(xpath_expression) > 0:
                xpath_expression += " and "
            xpath_expression += xpath_to_exclude % category
    return "//rss/channel/item[%s]" % xpath_expression