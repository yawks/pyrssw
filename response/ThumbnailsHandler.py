from response.RequestHandler import RequestHandler
import requests
import base64

#This handler get the first thumbnail of Google Images for any query.
class ThumbnailsHandler(RequestHandler):
    def __init__(self, url_prefix):
        super().__init__(url_prefix, "thumbnails", "https://www.google.fr/search?source=lnms&tbm=isch&q=")
    
    def getContent(self, url):
        content = ""
        response = requests.get(url, headers = super().getUserAgent())
       
        split = response.text.split("_setImgSrc(")
        if len(split) > 1:
            content = split[1].split(",")[2].replace("\\/","/").replace("\\x3d","=").split("'")[0]
            content = base64.b64decode(content.encode())
        
        return content
    
    def getContentType(self):
        return "image/webp"
