import lxml.etree


#get content of first found xpath in the list of xpath expressions
def getContent(dom: lxml.etree, xpaths: list) -> str:
    content = ""
    for xpath in xpaths:
        results = dom.xpath(xpath)
        if len(results) > 0:
            content = lxml.etree.tostring(results[0], encoding='unicode')
            break

    return content

#delete list of nodes
def deleteNodes(nodes):
    for node in list(nodes):
        node.getparent().remove(node)