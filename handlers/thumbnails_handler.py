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
     - url: make a thumbnail of the given url
     - blur: blur the thumbnail

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

        parsed = urlparse(path)
        if "url" in parse_qs(parsed.query):
            url = unquote_plus(parse_qs(parsed.query)["url"][0])
            if try_to_replace_amp:
                url = url.replace("&amp;", "&")
            content = requests.get(url).content
        else:
            # returns an empty image
            content = "R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="

        if (
            "blur" in parse_qs(parsed.query)
            and parse_qs(parsed.query)["blur"][0] == "true"
        ):
            try:
                img = Image.open(BytesIO(content))
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                img = img.resize((128, 128))
                blurred_image = img.filter(ImageFilter.BoxBlur(10))
                img_byte_arr = io.BytesIO()
                blurred_image.save(img_byte_arr, format="PNG")
                content = img_byte_arr.getvalue()
            except Exception as e:
                if "url" in parse_qs((parsed.query)) and not try_to_replace_amp:
                    content = self._get_content(path, True)
                else:
                    self._log(
                        "Unable to blur image (path: %s) (reason : '%s')"
                        % (path, str(e))
                    )

        return content
