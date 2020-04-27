from response.RequestHandler import RequestHandler
import lxml.etree
import requests
import re
import time

class IzismileHandler(RequestHandler):
    def __init__(self, prefix, server_name, server_port):
        super().__init__(prefix, server_name, server_port, "izismile", "https://izismile.com/")

    
    def getFeed(self, uri):
        feed = requests.get(url= "https://feeds2.feedburner.com/izismile", headers = {}).text
        feed = re.sub(r'<link>[^<]*</link>', '', feed)
        feed = feed.replace('<guid isPermaLink="false">', '<link>')
        feed = feed.replace('</guid>', '</link>')
        #feed = feed.replace('<title>Izismile.com</title>', '<title>Izismile.com revamp</title>')
        feed = feed.replace('<link>https://izismile.com/', '<link>' + self.url_prefix)
        
        return self._replaceURLs(feed)

    def getContent(self, url):
        content, url_next_page = self._getContent(url)

        if url_next_page != "":
            #add a page 2 (only page 2 which covers most of cases)
            next_content, url_next_page = self._getContent(url_next_page)
            content += next_content

        return super().getWrappedHTMLContent(content)
    

    def _getContent(self, url):
        url_next_page = ""
        page = self._getPageFromUrl(url)
        dom = lxml.etree.HTML(page.text)

        scripts = dom.xpath('//script')
        for script in scripts:
            script.getparent().remove(script)

        izi_videos = dom.xpath('//*[@class="s-spr icon icon-mp4"]')
        for izi_video in izi_videos:
            parent = izi_video.getparent()
            if "href" in parent.attrib:

                video = lxml.etree.Element("video")
                video.set("controls", "")
                video.set("preload", "auto")
                
                source =  lxml.etree.Element("source")
                source.set("src", parent.attrib["href"])
                video.append(source)
                parent.getparent().append(video)

                
        pagers = dom.xpath('//*[@class="postpages"]')
        if len(pagers) > 2:
            url_next_page = dom.xpath('//*[@class="postpages"]//a')[0].values()[0]
        for pager in list(pagers):
            pager.getparent().remove(pager)

        pagers = dom.xpath('//*[@id="pagination-nums"]')
        for pager in pagers:
            pager.getparent().remove(pager)


        post_lists = dom.xpath('//*[@id="post-list"]')
        if len(post_lists) > 0:
            content = self._replaceURLs(lxml.etree.tostring(dom.xpath('//*[@id="post-list"]')[0], encoding='unicode'))
        else:
            content = self._replaceURLs(lxml.etree.tostring(dom, encoding='unicode'))
        content = self._cleanContent(content)

        return content, url_next_page

    def _getPageFromUrl(self, url):
        page = requests.get(url= url, headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'})
        if page.text.find("You do not have access to the site.") > -1:
            time.sleep(0.1)
            page = requests.get(url= url, headers = {'User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'})
        return page
    
    def _cleanContent(self, c):
        content = c.replace('<div class="break"/>', '')
        content = content.replace('<div class="tools"/>', '')
        content = re.sub(r'<span class="sordering"><a class="back" href="#[^"]*"/><a name="[^"]*">[^<]*</a><a class="next" href="#[^"]*"/></span>', '', content)
        content = re.sub(r'<div class="imgbox">(.*)</div>', r"\1", content, flags=re.S)
        content = content.replace('id="post-list"', 'id="mainbody"')
        return content
    
    def _replaceURLs(self, c):
        content = c.replace("a href='https://izismile.com/", "a href='" + self.url_prefix)
        content = content.replace('a href="https://izismile.com/', 'a href="' + self.url_prefix)
        content = content.replace('href="/', 'href="https://izismile.com/')
        content = content.replace("href='/", "href='https://izismile.com/")
        content = content.replace('src="/', 'src="https://izismile.com/')
        content = content.replace("src='/", "src='https://izismile.com/")
        content = content.replace("<img", "<br/><br/><img")
        content = content.replace('<div class="tools" style="display: none;"/>', '<div class="tools" style="display: block;"/>')
        return content
