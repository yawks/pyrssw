import base64
import re
from urllib.parse import unquote_plus

import requests

from handlers.request_handler import RequestHandler
from storage.session_store import USER_AGENT


class ThumbnailHandler(RequestHandler):
    """Handler which get the first thumbnail of Google Images for any query.

    Handler name: thumbnails

    Content:
        base64 encoded image
    """

    def __init__(self, request: str):
        super().__init__()
        original_website: str = "https://www.google.fr/search?source=lnms&tbm=isch&q="

        content = b""

        if request.find("?request=") > -1:
            r = unquote_plus(request[len("?request="):].replace('\t',
                                                   '').replace('\n', '').strip())
            response = requests.get(
                original_website + r, headers={"User-Agent": USER_AGENT})

            split = response.text.split("_setImgSrc(")
            if len(split) > 1:
                content = split[1].split(",")[2].replace(
                    "\\/", "/").replace("\\x3d", "=").split("'")[0]
                content = base64.b64decode(content.encode())
            else:
                imgs = re.findall(">data:[^;]*;base64,([^<]*)", response.text)
                if len(imgs) > 0:
                    content = imgs[0]
                else:
                    # returns an empty image
                    content = "R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="
        else:
            # returns an empty image
            content = "R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="

        self.content_type = "image/webp"
        # TODO : improve this, and avoid type ignore
        self.contents = content  # type: ignore
