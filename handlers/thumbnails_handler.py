import base64
import re
from typing import Optional
from urllib.parse import unquote_plus
from PIL import ImageFilter
import requests
from urllib.parse import urlparse, parse_qs
from handlers.request_handler import RequestHandler
from storage.session_store import USER_AGENT
from PIL import Image
from io import BytesIO
import io


class ThumbnailHandler(RequestHandler):
    """Handler which get the first thumbnail of Google Images for any query.

    Handler name: thumbnails

    Content:
        base64 encoded image
    """

    def __init__(self, path: str, source_ip: Optional[str]):
        super().__init__(source_ip)
        original_website: str = "https://www.google.fr/search?source=lnms&tbm=isch&q="

        content = b""

        parsed = urlparse(path)
        if "request" in parse_qs(parsed.query):
            content = self._process_request(
                parse_qs(parsed.query)["request"][0], original_website)
        if "url" in parse_qs(parsed.query):
            content = requests.get(unquote_plus(
                parse_qs(parsed.query)["url"][0])).content
        else:
            # returns an empty image
            content = "R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="

        if "blur" in parse_qs(parsed.query) and parse_qs(parsed.query)["blur"][0] == "true":
            img = Image.open(BytesIO(content))
            img = img.resize((128, 128))
            blurred_image = img.filter(ImageFilter.BoxBlur(10))
            img_byte_arr = io.BytesIO()
            blurred_image.save(img_byte_arr, format='PNG')
            content = img_byte_arr.getvalue()

        self.content_type = "image/webp"
        # TODO : improve this, and avoid type ignore
        self.contents = content  # type: ignore

    def _process_request(self, request, original_website) -> bytes:
        content = b""
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

        return content
