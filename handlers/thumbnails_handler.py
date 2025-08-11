import io
from io import BytesIO
from typing import Optional
from urllib.parse import unquote_plus, urlparse, parse_qs
from PIL import ImageFilter
from PIL import Image
from utils.http_client import http_client
from handlers.request_handler import RequestHandler


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
            content = http_client.get(url).content
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
