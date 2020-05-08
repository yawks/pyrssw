import base64

import requests

from handlers.launcher_handler import USER_AGENT
from handlers.request_handler import RequestHandler


class ThumbnailHandler(RequestHandler):
    """Handler which get the first thumbnail of Google Images for any query.

    Handler name: thumbnails
     
    Content:
        base64 encoded image
    """
    
    def __init__(self, request: str):
        super().__init__()
        original_website : str = "https://www.google.fr/search?source=lnms&tbm=isch&q="
    
        content = b""
        
        if len(request) > 1:
            r = request[1:].replace('\t','').replace('\n','').strip()
            response = requests.get( original_website + r, headers = {"User-Agent" : USER_AGENT})

            split = response.text.split("_setImgSrc(")
            if len(split) > 1:
                content = split[1].split(",")[2].replace("\\/","/").replace("\\x3d","=").split("'")[0]
                content = base64.b64decode(content.encode())
        else: #returns an empty image
            content = base64.b64decode("R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==".encode())

        self.content_type = "image/webp"
        self.contents = content #type: ignore
