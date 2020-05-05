from response.RequestHandler import RequestHandler
import requests
import base64

#This handler get the first thumbnail of Google Images for any query.
class PyRSSWRequestHandler(RequestHandler):
    def __init__(self, url_prefix):
        super().__init__(url_prefix, handler_name="thumbnails", original_website="https://www.google.fr/search?source=lnms&tbm=isch&q=")

    def get_content(self, url: str, parameters: dict)  -> str:
        content = ""
        if "request" in parameters:
            request = parameters["request"].replace('\t','').replace('\n','').strip()
            response = requests.get( self.original_website + request, headers = super().get_user_agent())

            split = response.text.split("_setImgSrc(")
            if len(split) > 1:
                content = split[1].split(",")[2].replace("\\/","/").replace("\\x3d","=").split("'")[0]
                content = base64.b64decode(content.encode())

        self.content_type = "image/webp"
        return content
