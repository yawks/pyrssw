
import base64
import re
from typing import Optional
from urllib.parse import unquote_plus
from PIL import ImageFilter
import requests
from urllib.parse import urlparse, parse_qs
from handlers.request_handler import RequestHandler
from handlers.launcher_handler import USER_AGENT
from PIL import Image
from io import BytesIO
import io


class ThumbnailHandler(RequestHandler):
    """Thumbnail generator.

    Handler name: thumbnails
    Parameters:
     - request: get the first thumbnail of Google Images of the request keywords.
     - url: make a thumbnail of the given url
     - blur: blur the thumbnail

     "request" and "url" parameters are exclusive, but can both be used with blur

    Content:
        base64 encoded image
    """

    def __init__(self, path: str, source_ip: Optional[str]):
        super().__init__(source_ip)

        content = self._get_content(path)

        self.content_type = "image/webp"
        # TODO : improve this, and avoid type ignore
        self.contents = content  # type: ignore

    def _get_content(self, path: str, try_to_replace_amp: bool = False):
        content = b""
        original_website: str = "https://www.google.fr/search?source=lnms&tbm=isch&q="

        parsed = urlparse(path)
        if "request" in parse_qs(parsed.query):
            content = self._process_request(
                parse_qs(parsed.query)["request"][0], original_website)
        elif "url" in parse_qs(parsed.query):
            url = unquote_plus(parse_qs(parsed.query)["url"][0])
            if try_to_replace_amp:
                url = url.replace("&amp;", "&")
            content = requests.get(url).content
        else:
            # returns an empty image
            content = "R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="

        if "blur" in parse_qs(parsed.query) and parse_qs(parsed.query)["blur"][0] == "true":
            try:
                img = Image.open(BytesIO(content))
                img = img.resize((128, 128))
                blurred_image = img.filter(ImageFilter.BoxBlur(10))
                img_byte_arr = io.BytesIO()
                blurred_image.save(img_byte_arr, format='PNG')
                content = img_byte_arr.getvalue()
            except Exception as e:
                if "url" in parse_qs((parsed.query)) and not try_to_replace_amp:
                    content = self._get_content(path, True)
                else:
                    self._log(
                        "Unable to blur image (path: %s) (reason : '%s')" % (path, str(e)))

        return content

    def _process_request(self, request: str, original_website: str) -> bytes:
        content = b""
        r = unquote_plus(request.replace('\t',
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
